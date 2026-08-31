# LossGraph Intelligence Engines (Day 2)

Three sensors, evaluated independently and honestly on the held-out test
split from `data/output/`. Each targets a different part of the loss
process on purpose -- the point of Day 2 was to show they're
*complementary*, not redundant, before building the fusion layer (day 3).

## Run them

```bash
python3 -m ml.risk_model      # Engine 1: transaction risk (LightGBM)
python3 -m ml.graph_engine    # Engine 3: entity graph (NetworkX)
python3 -m ml.anomaly_engine  # Engine 4: merchant temporal anomalies
```

Each prints its held-out report and writes artifacts to `ml/artifacts/`
(gitignored -- regenerate rather than commit).

## Engine 1 -- Transaction Risk Model (`risk_model.py`)

LightGBM, trained on **pre-authorization features only** (`features.py`):
transaction attributes, plus customer/device/address history aggregates
computed with a strict `shift(1)`/running-count-before pattern so nothing
about a transaction's own future outcome leaks into its own row. Cold-start
customers fall back to merchant baselines (section 35).

**Test set (held out, never seen in training or threshold tuning):**
PR-AUC 0.57, ROC-AUC 0.81. Two thresholds are reported, tuned on val only:
F1-optimal and **net-economic-benefit-optimal** (section 10-11's actual
objective) -- they don't land in the same place, which is the point of
tuning against the real objective instead of a generic ML metric.

**What it catches vs. misses, by design:**
| scenario | test flag rate | why |
|---|---|---|
| `fraud_spike` | ~100% | obvious at authorization time: thin history, odd hour, high amount |
| `coordinated_return_ring` | partial | some velocity/newness signal, but the *return itself* hasn't happened yet |
| `chargeback_wave` | ~0% | the transaction looked completely normal when it occurred -- there is no transaction-time signal here by construction |

That last row isn't a weakness to fix -- it's the honest limit of any
real-time score, and exactly why engines 3 and 4 exist.

## Engine 3 -- Entity Graph (`graph_engine.py`)

Bipartite `customer <-> device/address` graph (product co-purchase is
deliberately excluded -- too weak/promiscuous a signal to cluster identity
on). Connected components get a heuristic risk score from outcome
concentration (return/dispute rate vs. merchant baseline), burstiness
(transactions/day within the component), and size -- not a trained model,
per the PRD's own guidance to start with graph algorithms before reaching
for a GNN.

**The load-bearing result:** `coordinated_return_ring` components score
**0.87** mean; `false_positive_trap` components -- built to be structurally
similar (shared device, elevated order value, 20-person cluster) --
score **0.41**. Same kind of shared-identity signal, correctly separated,
because outcome rate and burstiness (not "is there a shared device at all")
carry the actual signal. This is the empirical version of section 34's
thesis: unusual != malicious.

Building this required fixing a real generator bug first: the original
device/address pools were small enough that the *entire baseline
population* percolated into one connected component via incidental random
collisions (see `data/generation/entities.py` -- home assignment is now
collision-free by construction via `replace=False`, plus one-off IDs for
rare device switches). A graph engine evaluated against a giant component is
meaningless, so this was blocking, not cosmetic.

## Engine 4 -- Merchant Temporal Anomaly Engine (`anomaly_engine.py`)

Daily return/dispute counts per merchant, tracked by the day the *outcome*
landed (not the order date) -- this is what makes `chargeback_wave`
detectable at all, since it has zero transaction-time signal. Anomaly score
is a Poisson-style z-score against a trailing pooled baseline rate
(`expected = baseline_rate * volume`, `z = (count - expected) / sqrt(expected)`),
not a naive z-score on the daily ratio -- the naive version false-alarms
constantly on quiet days (a 40-order day with 6 returns looks like a wild
15% rate next to a 3% baseline, but 6 vs. an expected ~1.2 is unremarkable
Poisson noise).

**Test-split loss-event detection: 83% (5/6)**, mean delay ~1-3 days for
return/graph-visible events. This engine is a **"something changed"**
detector, not a **"here's who"** detector -- it correctly also fires on
`seasonal_return_spike` and fires *sometimes* on other legitimate-but-busy
edge cases. That's expected, not a bug: distinguishing a genuine loss event
from a legitimate rate change needs the graph engine's cluster signal,
which is exactly why day 3 fuses the two rather than acting on either
alone (PRD section 15: "the anomaly engine doesn't stop there -- it
forwards the event to the graph engine").

## Honest limitations (documented, not hidden)

- Demo-scale data (12 merchants, ~2,500 customers) means scenario windows
  can still occasionally overlap in time on the same merchant, which
  confounds *attribution* of an anomaly flag to a single cause. Detection
  recall/latency numbers above are still meaningful; don't over-read
  precision on any single flagged day.
- Engine 1's economic report uses a merchant-averaged false-positive/
  verification cost, not per-merchant. Per-merchant policy optimization is
  day 3's action optimizer.
- `graph_engine.py`'s risk score is a hand-set heuristic weighting
  (0.5 outcome + 0.35 burstiness + 0.15 size), not fit to data. Reasonable
  starting weights, not claimed as optimal.

## Next (day 3)

Fuse the three scores into a Risk Event Genome (structured evidence chain
+ exposure estimate), then the counterfactual policy simulator and action
optimizer that actually minimize expected economic cost per section 10-11.
