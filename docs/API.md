# API Reference

Base URL: `http://localhost:8000/api/v1`. Interactive docs at `/docs`
(FastAPI's generated Swagger UI) once the backend is running. All
endpoints below read from `ml/artifacts/loss_events_with_policy.json` and
`data/output/*.csv` via `backend/app/data_access.py` -- run `make
pipeline` first, or every route returns `503` with a message telling you
to.

## Active endpoints (real data, wired to the dashboard)

### `GET /risk/incidents?merchant_id=ALL`

Command Center: summary metrics + incident list, optionally scoped to one
merchant.

```json
{
  "merchant_id": "ALL",
  "current_exposure": 1198572.82,
  "preventable_exposure": 603129.46,
  "active_incidents": 9,
  "total_incidents": 17,
  "net_benefit_vs_allow": 560806.69,
  "incidents": [
    {
      "event_id": "RE-2026-00013", "source": "temporal", "event_type": "chargeback_wave",
      "merchant_id": "M001", "merchant_name": "Electronics Store 1",
      "confidence": 1.0, "exposure_estimate": 523563.60,
      "affected_transaction_count": 51, "affected_customer_count": 47,
      "recommended_action": "verify"
    }
  ]
}
```

### `GET /risk/incidents/{event_id}`

Full Risk Event Genome: evidence chain, ground-truth cross-check
(evaluation-only), counterfactual simulations. See `docs/DATA_MODEL.md`
for the full shape.

### `GET /risk/incidents/{event_id}/graph`

Cytoscape-ready `{nodes, edges}` for a cluster event's entity graph.
Temporal events (no qualifying cluster) return `{"nodes": [], "edges":
[]}` -- that emptiness is itself evidence (see the event's `E2` claim).

### `GET /risk/simulate/{event_id}/compare`

The counterfactual policy comparison (all 6 candidate actions +
recommendation + reason), re-served from the same precomputed
`counterfactual` field for a cleaner separation of concerns in the
frontend.

### `GET /risk/merchants`

Merchant list for the dashboard's selector dropdown, with incident counts.

### `GET /health`, `GET /health/ready`

Standard health checks.

## Endpoints present but not wired to real data

`api/transaction.py` (single-transaction real-time scoring),
`api/entity.py` (generic entity lookup by ID), and `api/chargeback.py`
(evidence generation) remain from the original scaffold, still return
placeholder/mock responses, and query the (empty) SQLAlchemy DB rather
than the pipeline artifacts. Not required by the demo's "killer moment"
flow (Command Center -> investigate -> simulate); left unfinished rather
than removed so the intended shape is visible. See `docs/ARCHITECTURE.md`
for what was cut and why.
