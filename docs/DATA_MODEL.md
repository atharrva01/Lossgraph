# Data Model

Two layers: the **synthetic dataset** (`data/output/`, produced by
`data/generation/`) and the **pipeline output** (`ml/artifacts/`, produced
by `ml/`) that the backend actually serves. A third schema --
`backend/app/models.py`'s SQLAlchemy models -- describes the same entities
for an intended live-ingestion deployment but is not the active data path
today (see `docs/ARCHITECTURE.md`).

## Synthetic dataset (`data/output/`)

| File | Grain | Key columns |
|---|---|---|
| `merchants.csv` | 1 row/merchant | `merchant_id`, `category`, `avg_order_value`, `baseline_return_rate`, `baseline_chargeback_rate`, `baseline_fraud_rate`, `false_positive_cost`, `verification_cost`, `risk_tolerance` |
| `customers.csv` | 1 row/customer | `customer_id`, `merchant_id`, `created_at`, `home_device_id`, `home_address_id`, `true_archetype` (ground truth), `scenario_id` (ground truth) |
| `devices.csv` / `addresses.csv` / `products.csv` | 1 row/entity | `device_id`/`address_id`/`product_id`, type/category fields |
| `transactions.csv` | 1 row/transaction | `transaction_id`, `merchant_id`, `customer_id`, `amount`, `timestamp`, `device_id`, `address_id`, `product_id`, `is_returned`/`returned_at`, `is_disputed`/`disputed_at`, `split` (train/val/test). **No `is_fraud` column** -- see below. |
| `entities.csv` | 1 row/entity (all types) | `entity_id`, `entity_type` (customer/device/address/product), `first_seen`, `last_seen` -- derived from `transactions.csv`, not scenario-aware |
| `relationships.csv` | 1 row/(customer, entity) pair observed | `source_entity_id`, `target_entity_id`, `relationship_type` (USED_DEVICE/USED_ADDRESS/BOUGHT_PRODUCT), `first_seen`, `last_seen`, `frequency`, `confidence` -- bipartite, not pairwise customer-customer (see `data/README.md` for why) |
| `ground_truth/transaction_labels.csv` | 1 row/transaction | `transaction_id`, `is_fraud`, `scenario_id`, `scenario_type`, `category` (normal/loss/edge_case). Evaluation-only; never joined into model features. |
| `ground_truth/scenario_manifest.json` | 1 record/injected scenario instance | onset time, window, exposure, affected entities, split -- used to compute detection recall/latency in `docs/EVALUATION.md` |

**Why labels are a separate file, not a column:** `transactions.csv` is
what `ml/features.py` reads to build the model's feature matrix. Physically
separating the label makes leakage a file you didn't read from, not a
column you forgot to drop.

## Pipeline output (`ml/artifacts/`)

| File | Produced by | Contents |
|---|---|---|
| `test_risk_scores.csv` | `risk_model.py` | `transaction_id`, `risk_score` (test split only) |
| `graph_components.csv` / `graph_transaction_scores.csv` | `graph_engine.py` | component stats (size, return/dispute ratio, burstiness, score) / per-transaction score + `component_id` |
| `merchant_daily_anomaly.csv` | `anomaly_engine.py` | per (merchant, date): order/return/dispute counts, z-scores, `is_anomalous` |
| `fused_scores.csv` | `fusion.py` | per test-split transaction: all four scores (`risk_score`, `graph_risk_score`, `anomaly_score`, `fused_score`) |
| `loss_events_with_policy.json` | `loss_events.py` + `counterfactual.py` | **the object the API and dashboard actually serve** -- one record per detected event: |

```jsonc
{
  "event_id": "RE-2026-00002",
  "source": "cluster" | "temporal",
  "event_type": "coordinated_return_ring" | "chargeback_wave" | ...,
  "merchant_id": "M003",
  "confidence": 0.989,
  "exposure_estimate": 187828.49,       // probability-weighted
  "gross_amount_at_risk": 189790.20,    // unweighted
  "affected_transaction_count": 15,
  "affected_customer_count": 7,
  "primary_driver": "SKU-00476",
  "evidence": [{ "id": "E1", "claim": "...", "data": {...} }, ...],
  "transaction_ids": ["TXN-...", ...],
  "ground_truth": { "purity": 1.0, "dominant_true_scenario": "...", ... },  // evaluation-only
  "counterfactual": {
    "recommended_action": "block",
    "simulations": [{ "action": "allow", "net_benefit": 0.0, ... }, ...]
  }
}
```

## Backend DB schema (`backend/app/models.py`) -- intended, not active

SQLAlchemy models for `Merchant`, `Customer`, `Transaction`, `Entity`,
`Relationship`, `RiskEvent`, `Counterfactual` exist and describe the
intended schema for a live-ingestion deployment (a `RiskEvent` row per
`loss_events.json` record, etc.), but nothing currently loads
`data/output/`/`ml/artifacts/` into them -- `backend/app/data_access.py`
reads the files directly. One pre-existing bug fixed while wiring the
backend: `Entity.metadata` collided with SQLAlchemy's reserved
`Base.metadata` attribute and prevented the app from importing at all;
renamed to `entity_metadata`.
