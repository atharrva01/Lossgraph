# Architecture

This describes the system as built, not as originally envisioned. Where
the two differ, the difference is called out with the reasoning -- a
5-day solo build against a Sep 5 deadline required cutting real scope
(Neo4j, LLM investigator, chargeback responder, live Razorpay integration,
authentication) to what's actually gradeable: a working detector, held-out
precision/recall, honest false-positive cost, and a strictly defensive
system. See `ROADMAP.md` for the day-by-day build log and `docs/
EVALUATION.md` for the numbers this architecture produces.

## System diagram (as built)

```
data/generation/                          ml/
┌──────────────────────┐                  ┌─────────────────────────┐
│ Synthetic merchant    │                  │ Engine 1: risk_model.py │
│ ecosystem generator   │──── CSV/JSON ───▶│  LightGBM, pre-auth     │
│ (baseline behaviour + │     data/output/ │  features only          │
│  10 injected scenario │                  ├─────────────────────────┤
│  types, chronological │                  │ Engine 3: graph_engine  │
│  train/val/test)      │                  │  NetworkX bipartite     │
└──────────────────────┘                   │  customer<->device/     │
                                            │  address graph          │
                                            ├─────────────────────────┤
                                            │ Engine 4: anomaly_engine│
                                            │  Poisson rolling        │
                                            │  z-score, per merchant  │
                                            └────────────┬────────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │ fusion.py            │
                                              │ noisy-OR combination │
                                              └──────────┬──────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │ loss_events.py       │
                                              │ Risk Event Genome:   │
                                              │ evidence chain,      │
                                              │ exposure, confidence │
                                              └──────────┬──────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │ counterfactual.py    │
                                              │ 6-policy simulation, │
                                              │ economically-optimal │
                                              │ action recommendation│
                                              └──────────┬──────────┘
                                                         │
                                          ml/artifacts/loss_events_with_policy.json
                                                         │
                        backend/app/data_access.py ──────┘  (loads once, serves via REST)
                                    │
                        FastAPI (backend/app/api/*.py)
                                    │
                        Next.js dashboard (frontend/src/app/*)
                        Command Center -> incident drill-down
                        (evidence chain, Cytoscape.js graph,
                         policy comparison)
```

**Why offline pipeline + served artifacts, not live scoring.** The
intelligence pipeline (`data/generation/` + `ml/`) is a batch process --
exactly like a real risk system's nightly/streaming scoring job. The API's
job is to serve its output (`backend/app/data_access.py` loads the JSON
once and caches it), not recompute three ML engines per HTTP request. Run
`make pipeline` to regenerate; the backend picks up the new artifacts on
restart.

## The three engines, and why three

A conventional fraud model asks "is this transaction risky?" using one
signal source. This system asks the same question from three
independent angles because each one sees a different part of the loss
process and misses the others by construction, verified empirically (see
`docs/EVALUATION.md`):

| Engine | Sees | Blind to |
|---|---|---|
| Transaction risk model (LightGBM, pre-auth features only) | obvious authorization-time fraud (`fraud_spike`: ~100% caught) | outcomes that haven't happened yet (`chargeback_wave`: ~0% caught -- the transaction looked completely normal when it occurred) |
| Entity graph (NetworkX, bipartite customer<->device/address) | shared-infrastructure clusters with elevated, bursty outcome rates (`coordinated_return_ring`) | anything that doesn't cluster (`fraud_spike`, `chargeback_wave`: 0.0 graph score by construction) |
| Temporal anomaly (Poisson rolling z-score on daily outcome counts) | rate changes in the outcome stream, the only way `chargeback_wave` is detectable at all | *why* the rate changed -- fires on legitimate seasonal/promo spikes too |

Fusion (`fusion.py`) combines them via noisy-OR rather than a fourth
trained model, specifically so a judge (or an ops analyst) can trace any
flagged transaction back to which engine(s) actually raised it. PR-AUC
after fusion (0.61) beats every individual engine, confirming the three
signals are complementary rather than redundant.

## Loss Event Genome

`loss_events.py` turns per-transaction fused scores into the object the
rest of the system actually reasons about: a **Loss Event**, not a
transaction. Two construction paths:

- **Cluster events** -- a graph component scoring above threshold (and
  above a minimum size, to reject noise from small-scale legitimate
  device/address sharing -- see `ml/README.md` for how this was found).
- **Temporal events** -- a merchant-day anomaly not already explained by a
  cluster event's own date range, so `chargeback_wave` and diffuse return
  spikes still produce an event even with zero graph signal.

Every event carries a structured, numbered evidence chain (`E1`, `E2`, ...)
where each claim maps to an underlying data value -- displayed expandable
in the dashboard's incident drill-down, matching the product's "why do you
believe this?" trust requirement.

## Counterfactual Simulator + Action Optimizer

`counterfactual.py` simulates six candidate actions per event (allow,
monitor, verify, hold, block, investigate_cluster) and recommends whichever
maximizes net economic benefit, using the merchant's own
`false_positive_cost` / `verification_cost` -- not a fixed score
threshold. The one modeling decision that mattered most: **BLOCK charges
the full order amount for a wrongly-blocked legitimate transaction (a lost
sale), not the same flat friction fee as VERIFY/HOLD.** Without that
distinction, BLOCK won even on the deliberately-ambiguous
`false_positive_trap` cluster -- exactly the failure mode the product spec
exists to prevent.

## Backend and frontend

- **Backend** (`backend/app/`): FastAPI. `data_access.py` is the only file
  that touches `data/output/` and `ml/artifacts/`; every router
  (`api/incident.py`, `api/simulation.py`, `api/merchants.py`) is a thin
  read layer over it. `api/transaction.py`, `api/entity.py`,
  `api/chargeback.py` remain from the original scaffold and are not wired
  to real data -- the chargeback responder in particular is unbuilt (see
  Roadmap).
- **Frontend** (`frontend/src/`): Next.js App Router. `app/page.tsx`
  (Command Center) -> `app/incidents/[id]/page.tsx` (drill-down), with
  `components/GraphView.tsx` wrapping `cytoscape` directly (no third-party
  React wrapper -- the originally-scaffolded `cytoscape-react` package
  doesn't exist on npm) and `components/PolicyComparison.tsx` rendering
  the counterfactual table with the recommended action highlighted.

## Data model

See `docs/DATA_MODEL.md`. The synthetic dataset (`data/output/*.csv`) and
the SQLAlchemy models in `backend/app/models.py` describe the same
entities (merchants, customers, transactions, entities, relationships,
risk events) but are **not currently the same data path** -- the dashboard
is served from the CSV/JSON pipeline output, not a populated database. The
DB models exist as the intended schema for a live-ingestion deployment,
not as dead code, but loading them is unbuilt.

## What the original vision (PRD) included that this doesn't

Cut deliberately, for a 5-day timeline, not by accident:

- **LLM investigator narrative.** The evidence chain is deterministic and
  structured (see above) -- it satisfies the "evidence-grounded
  explanation" requirement without an LLM call the demo would depend on
  succeeding live. Adding a narrative layer on top is additive, not
  foundational.
- **Chargeback responder + evidence contradiction detector.** Downstream
  of loss-event detection, not required by the graded rubric (a working
  detector + held-out eval + honest FP cost + defense-only).
- **Neo4j, Docker Compose, authentication, multi-tenant support.**
  Infrastructure that adds deployment risk without adding evaluation
  signal for a synthetic-data demo.
- **Live Razorpay API integration.** The system is demonstrated entirely
  against synthetic data; no claim of access to real transaction data is
  made anywhere in this repo.
