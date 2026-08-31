# LossGraph Synthetic Data Generator

Generates the synthetic merchant ecosystem the rest of LossGraph is trained
and evaluated against, per PRD sections 32-34: baseline entities and normal
behaviour, then independently-labelled loss processes and legitimate-but-
unusual edge cases layered on top.

## Run it

```bash
python3 -m data.generation.generate --scale demo --seed 42
```

Output lands in `data/output/` (~3s, ~28k transactions at demo scale).
`--scale full` targets the PRD's full ecosystem size (50k customers / 500k
transactions) -- not needed for the buildathon demo, but the same pipeline.

## Design decisions

**Chronological split, not random.** `--train-days/--val-days/--test-days`
(default 60/15/25) partition a single continuous timeline. Every injected
scenario is instantiated *separately per split* -- train's fraud rings are
different customers/devices/timestamps than test's -- so the held-out test
set never leaks specific fraud instances the model trained on, only the
general *pattern*.

**Labels are physically separated from features.** `transactions.csv` (the
feature table) has no `is_fraud` / `scenario_id` / `scenario_type` columns.
Those live only in `ground_truth/transaction_labels.csv`, joined by
`transaction_id`, and are for the evaluation harness only. This makes label
leakage a file you didn't read from, not a column you forgot to drop.

**Relationships are bipartite, not pairwise.** `relationships.csv` encodes
`customer -> device/address/product` edges with temporal metadata
(first_seen, last_seen, frequency, confidence). Customer-customer clustering
(e.g. "these 7 customers share a device") is a *projection* the graph engine
computes, not something pre-materialized here -- avoids O(n^2) edges on
popular shared devices, and matches how a real ingestion pipeline works.

**Scenario configs are declarative.** Each `data/scenarios/*.json` names a
scenario type, how many instances to inject per split, and default
parameters. Add a new scenario type by writing a config + one function in
`data/generation/scenarios.py` registered in `SCENARIO_REGISTRY`.

## Scenario types

| Type | Category | Mechanic | Proves |
|---|---|---|---|
| `coordinated_return_ring` | loss | new accounts, shared devices, burst orders on one SKU, high return/dispute rate | graph + temporal signal fused |
| `fraud_spike` | loss | short burst of high-decline, high-dispute transactions, late-night bias | pure temporal/velocity signal (no shared entities) |
| `chargeback_wave` | loss | earlier real transactions disputed together weeks later | delayed-loss detection, chargeback linkage |
| `false_positive_trap` | edge case | high-value customers sharing a device, steady 14-day activity, normal outcomes | shared device != fraud |
| `household_address_sharing` | edge case | family sharing one address, normal outcomes | shared address != fraud |
| `corporate_device_sharing` | edge case | employees sharing 2 devices, business hours only, low returns | shared device + B2B pattern != fraud |
| `viral_product_spike` | edge case | many unrelated new customers buying one SKU, no shared entities | SKU concentration alone != fraud |
| `new_customer_cold_start` | edge case | brand-new customers, single order each | newness alone != risk |
| `promotional_campaign_spike` | edge case | broad discount-driven volume spike across existing customers | volume spike != fraud spike |
| `seasonal_return_spike` | edge case | broad-based return-rate rise, no entity clustering | return-rate spike != fraud |

`false_positive_trap` and `coordinated_return_ring` are deliberately built to
look structurally similar (shared device, elevated order value) so a model
that only checks "is there a shared device" fails both precision and the
buildathon's honest-false-positive-cost requirement; distinguishing them
requires burstiness + outcome signal, which is exactly what the temporal and
graph engines need to fuse.

## Output layout

```
data/output/
  merchants.csv customers.csv devices.csv addresses.csv products.csv
  transactions.csv        # features only -- no fraud/scenario labels
  entities.csv             # customer/device/address/product nodes
  relationships.csv        # bipartite temporal edges
  ground_truth/
    transaction_labels.csv # transaction_id -> is_fraud, scenario_id, scenario_type, category
    scenario_manifest.json # one record per injected instance: onset time,
                            # exposure, affected entities -- used for
                            # detection-precision/recall/latency evaluation
  summary.json              # counts, split sizes, label/scenario breakdowns
```

## Not built (deliberate scope cut for the 5-day buildathon timeline)

`new_merchant_cold_start` (PRD section 34) is not implemented -- it needs a
mid-stream merchant + product catalog append that the other scenarios don't,
and cold-start handling for existing merchants (`new_customer_cold_start`)
already covers the same "thin history != risk" evaluation point.
