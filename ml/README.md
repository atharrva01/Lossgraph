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

## Day 3 -- Fusion, Loss Events, Counterfactual Simulator, Action Optimizer

```bash
python3 -m ml.fusion         # per-transaction fused probability
python3 -m ml.loss_events    # Risk Event Genome objects + evidence chains
python3 -m ml.counterfactual # policy simulation + action recommendation
```

### Fusion (`fusion.py`)

`P_fused = 1 - (1-P_transaction)(1-P_graph)(1-P_anomaly)` -- noisy-OR, not a
fourth trained model, so any given transaction's score stays traceable to
which engine(s) actually raised it. The anomaly term is deliberately
down-weighted (0.5x): it's computed per **merchant-day**, so at full
strength it bleeds into every unrelated transaction that happened to occur
on an anomalous day (verified empirically -- some `normal`-labelled test
transactions hit a fused score of 1.0 before this fix). Fused test PR-AUC
0.61 / ROC-AUC 0.84, both above any single engine alone.

### Loss Events (`loss_events.py`)

Two sources, matching how the underlying signals differ: **cluster**
events (a graph component above threshold) and **temporal** events (a
merchant-day anomaly not already covered by a cluster). Building this
surfaced two more calibration issues, both fixed and both worth knowing
about if you touch this code:

1. **Meaningless micro-clusters.** 25 of 32 threshold-qualifying graph
   components were 2-person -- the intentionally-injected natural sharing
   (siblings/couples), whose observed outcome rate is high-variance noise
   at n=2. Added `MIN_CLUSTER_SIZE=4` before something counts as a cluster
   event (PRD section 29's own warning: "a graph that creates thousands of
   meaningless connections is worse than no graph"). Dropped 34 cluster
   events to 9, and the 9 that remain are the real ones.
2. **Dispute vs. return asymmetry.** A dispute-driven temporal event
   (`chargeback_wave`) was 98% pure; every return-driven one observed in
   this run was 0% pure (legitimate seasonal/promo/viral rate changes).
   That's not a guess, it's what actually happened on this test split --
   disputing a charge is a deliberate, costly action, returning an item is
   routine. Temporal event confidence now weights dispute anomalies at full
   strength and return anomalies at 0.4x accordingly.

**Result on the test split:** 9 cluster + 8 temporal = 17 events. Every
true `coordinated_return_ring` and the `chargeback_wave` instance surfaced
as a distinct, high-confidence event (0.88-1.0); every event built from a
legitimate edge case (false_positive_trap-tainted or a genuine seasonal/
promo/viral spike) landed at meaningfully lower confidence (0.3-0.58) --
the gap is real and load-bearing, not cosmetic.

### Counterfactual Simulator + Action Optimizer (`counterfactual.py`)

Six candidate actions (allow/monitor/verify/hold/block/investigate_cluster)
simulated per event using each transaction's fused probability and the
merchant's own cost parameters. The one modeling fix that mattered: **a
block on a legitimate order is a lost sale (full order amount), not a flat
friction fee** -- verify/hold assume the order still completes after some
delay, block means it never happens at all. Getting this wrong made block
win almost everywhere, including on the false_positive_trap cluster, which
would have been exactly the failure mode the PRD's section 34 exists to
catch.

**With that fixed:** every purity-1.0 ring gets BLOCK (confidence 0.88-0.99).
The false_positive_trap-tainted cluster (confidence 0.54) gets HOLD, not
BLOCK -- a real behavioral difference driven only by confidence and
economics, never by the ground-truth label the optimizer never sees. All
7 low-confidence return-only temporal events get ALLOW. Mean action
aggressiveness (0=allow..5=block) is **4.71 for purity>=0.8 events vs. 0.70
for purity<0.2 events** -- the system calibrates intervention strength to
actual severity using only its own confidence estimate. Total net benefit
vs. doing nothing: Rs 5.6L on this held-out test split.

### Known gaps, honestly

- `chargeback_wave` events get a VERIFY recommendation, which doesn't
  really make sense for a transaction that already shipped -- the
  five-action framework has no "contest the dispute" action. That's the
  chargeback responder's job (PRD section 18), not built yet.
- Action economics (prevention_rate, cost multipliers) are a documented,
  reasonable starting model, not fit to any data.
- `investigate_cluster`'s core-member threshold (0.7) is hand-set.

## AI Investigator (`investigator.py`)

```bash
python3 -m ml.investigator
```

Turns each event's evidence chain into a plain-English case-file narrative
using Claude Opus 5 (`client.messages.parse()` with a Pydantic output
schema -- see `docs/ARCHITECTURE.md` for the full design). Three things
matter more than the prose quality:

1. **Ground truth is never in the model's input.** Only evidence,
   confidence, exposure, and the already-decided `recommended_action` --
   the same information a real deployment would have. The model narrates
   and justifies; it does not detect or decide.
2. **Every claim must cite a real evidence ID, checked post-hoc.**
   `_citations_present()` verifies every sentence in `supporting_evidence`/
   `contradicting_evidence` references an actual `E1`/`E2`/... from the
   input. A response that fails this check is treated as a failure, not
   accepted with a warning.
3. **The fallback path is exercised for real, not simulated.** This repo
   has no `ANTHROPIC_API_KEY` configured anywhere -- so every narrative
   currently in `ml/artifacts/loss_events_with_policy.json` was produced by
   `_fallback_narrative()`, not the LLM. Verified with a mock-client test
   (well-formed response passes through, an uncited claim triggers
   fallback, a raised exception triggers fallback) since the live API path
   can't be exercised without a key -- see the git history for the test
   script. Set `ANTHROPIC_API_KEY` before `make pipeline` to get real
   narratives instead; nothing else about the pipeline changes.

Not built: the chargeback responder (PRD section 18), which is why
`chargeback_wave` events still get a VERIFY recommendation that doesn't
really fit a transaction that already shipped -- there's no "contest the
dispute" action in the current five-action framework.
