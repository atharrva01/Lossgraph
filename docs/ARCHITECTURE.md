# Architecture

This describes the system as built, not as originally envisioned. Where
the two differ, the difference is called out with the reasoning -- a
solo build against a Sep 5 deadline required cutting real scope (Neo4j,
live Razorpay integration, authentication) to what's actually gradeable:
a working detector, held-out precision/recall, honest false-positive
cost, and a strictly defensive system. See `ROADMAP.md` for the
day-by-day build log and `docs/EVALUATION.md` for the numbers this
architecture produces.

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
                                              ┌──────────▼──────────┐
                                              │ investigator.py      │
                                              │ Claude Opus 5 case-  │
                                              │ file narrative,      │
                                              │ citation-checked,    │
                                              │ deterministic fallback│
                                              └──────────┬──────────┘
                                                         │
                                          ml/artifacts/loss_events_with_policy.json
                                                         │
                                              ┌──────────▼──────────┐
                                              │ chargeback_responder │
                                              │ .py: per-dispute     │
                                              │ evidence + contra-   │
                                              │ diction check, links │
                                              │ back to Loss Events  │
                                              └──────────┬──────────┘
                                                         │
                                          ml/artifacts/chargeback_cases.json
                                                         │
                        backend/app/data_access.py ──────┘  (loads once, serves via REST)
                                    │
                        FastAPI (backend/app/api/*.py)
                                    │
                        Next.js dashboard (frontend/src/app/*)
                        Command Center -> incident drill-down
                        (evidence chain, Cytoscape.js graph,
                         policy comparison, linked chargebacks)
                        + a separate Chargebacks section
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

## AI Investigator

`investigator.py` calls Claude Opus 5 to turn the evidence chain into a
plain-English case-file narrative (incident summary, primary hypothesis,
supporting/contradicting evidence, unknowns, confidence commentary). It
investigates evidence; it does not detect anything itself and cannot
override the deterministic recommendation:

- **Input is restricted by construction.** The model receives the evidence
  chain, confidence, exposure, and the already-computed `recommended_action`
  -- never `ground_truth`. A real deployment doesn't have the oracle label;
  including it here would let the model parrot the answer instead of
  reasoning from evidence, defeating the point of testing whether the
  narrative stays grounded.
- **Structured output, not free text.** `client.messages.parse()` with a
  Pydantic schema (`InvestigationNarrative`) guarantees a typed response;
  the system prompt requires every claim in `supporting_evidence` /
  `contradicting_evidence` to cite an evidence ID in parentheses.
- **Grounding is checked, not just requested.** After parsing, every
  citation is verified to reference a real evidence ID from the input
  (`_citations_present`); a response that fails this check is treated as a
  failure and falls through to the same path as an API error.
- **Failure handling is real, not simulated.** No `ANTHROPIC_API_KEY` is
  configured anywhere in this repo or its environment, so every narrative
  currently on disk was produced by the deterministic fallback --
  evidence-complete, clearly labelled `deterministic_fallback` in the data
  and in the dashboard's "AI Investigation" panel, generated with zero API
  calls. This is section 43's "LLM unavailable" failure path exercised for
  real, not asserted.

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

## Chargeback Responder

`chargeback_responder.py` closes the loop the product spec's demo script
describes: a dispute arrives, and the system checks whether it already
knows something about the transaction, instead of treating every
chargeback as a fresh case with no memory of prior detection.

For each disputed transaction (test split, matching the rest of this
repo's held-out evaluation -- `loss_events_with_policy.json` and
`fused_scores.csv` only exist for that split): an evidence checklist
scoped to what the reason code actually requires (a `duplicate_charge`
dispute doesn't need a delivery confirmation; an `unauthorized` one does
need device-consistency evidence, not a product listing), a check for
contradictions in the merchant's own records (a refund already issued
before the dispute; the transaction independently flagged as high-risk by
this same pipeline), and a CONTEST / ACCEPT / ESCALATE recommendation.

**The recommendation reuses detection, it doesn't redo it.** A transaction
linked to a high-confidence Loss Event -- or, when it wasn't swept into a
formal cluster/temporal event, one whose own fused risk score is elevated
-- gets ACCEPT: contesting would mean arguing against this same system's
own independent finding. Every ACCEPT recommendation in this repo's data
was verified correct against ground truth (`docs/EVALUATION.md`), and each
case links back to its Loss Event (visible on both the case page and the
event's own drill-down, as a "Linked Chargebacks" list) -- the "this
dispute is connected to Loss Event #871" moment from the product spec,
working end to end rather than narrated over a mockup.

An optional Claude Opus 5 call drafts the response prose from an
already-decided case file, with the same discipline as the AI Investigator
above: no ground truth in its input, must acknowledge any listed
contradiction, cannot argue for a different recommendation than the one
already chosen, and falls back to a deterministic template on any failure
-- exercised for real in this repo, same as the investigator, since no
API key is configured anywhere in this environment.

## Backend and frontend

- **Backend** (`backend/app/`): FastAPI. `data_access.py` is the only file
  that touches `data/output/` and `ml/artifacts/`; every router
  (`api/incident.py`, `api/simulation.py`, `api/merchants.py`,
  `api/chargeback.py`) is a thin read layer over it. `api/transaction.py`
  and `api/entity.py` remain from the original scaffold and are not wired
  to real data.
- **Frontend** (`frontend/src/`): Next.js App Router. `app/page.tsx`
  (Command Center) -> `app/incidents/[id]/page.tsx` (drill-down) and
  `app/chargebacks/` (list + case detail, cross-linked with the incident
  it traces to), with `components/GraphView.tsx` wrapping `cytoscape`
  directly (no third-party React wrapper -- the originally-scaffolded
  `cytoscape-react` package doesn't exist on npm) and
  `components/PolicyComparison.tsx` rendering the counterfactual table
  with the recommended action highlighted.

## Data model

See `docs/DATA_MODEL.md`. The synthetic dataset (`data/output/*.csv`) and
the SQLAlchemy models in `backend/app/models.py` describe the same
entities (merchants, customers, transactions, entities, relationships,
risk events) but are **not currently the same data path** -- the dashboard
is served from the CSV/JSON pipeline output, not a populated database. The
DB models exist as the intended schema for a live-ingestion deployment,
not as dead code, but loading them is unbuilt.

## What the original vision (PRD) included that this doesn't

Cut deliberately, not by accident:

- **Neo4j, Docker Compose, authentication, multi-tenant support.**
  Infrastructure that adds deployment risk without adding evaluation
  signal for a synthetic-data demo.
- **Live Razorpay API integration.** The system is demonstrated entirely
  against synthetic data; no claim of access to real transaction data is
  made anywhere in this repo.
