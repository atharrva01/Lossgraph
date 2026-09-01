# LossGraph

**AI Risk Manager for Merchant Loss Intelligence**

Don't just score risky transactions. Understand how losses form, spread, and how to stop them.

## Overview

LossGraph is an AI-powered merchant risk intelligence system that detects, investigates and responds to emerging loss events across transactions, returns, refunds, chargebacks and coordinated abuse.

Unlike conventional fraud models that assign a risk score to individual transactions, LossGraph treats merchant risk as a **temporal, relational and evolving phenomenon**, building a continuously updated **Merchant Risk Graph** that connects transactions, customers, orders, devices, addresses, payment instruments, products, returns, refunds, and chargebacks.

## Key Features (built and running -- see `docs/ARCHITECTURE.md` for what wasn't)

- **Transaction Intelligence**: LightGBM risk model on leakage-safe, pre-authorization features
- **Network Intelligence**: NetworkX entity graph detecting coordinated abuse clusters, empirically separated from legitimate shared-device patterns (`docs/EVALUATION.md`)
- **Temporal Intelligence**: Poisson-style anomaly detection on merchant-level return/dispute rates, the only signal that catches chargeback waves
- **Risk Fusion**: noisy-OR combination of all three, interpretable back to source
- **Loss Event Genome**: structured, evidence-chained incidents (not raw transaction scores) with exposure estimates
- **Counterfactual Reasoning**: 6-policy simulation per event, economically-optimal action recommendation
- **AI Investigator**: Claude Opus 5 writes an evidence-grounded case-file narrative per event (citation-checked, never sees ground truth, cannot override the deterministic recommendation), with a verified deterministic fallback when no API key is configured
- **Chargeback Responder**: evidence checklist + contradiction detection per dispute, cross-referenced against this system's own loss-event detection -- 74/74 ACCEPT recommendations verified correct against ground truth, each linked back to the Loss Event it traces to
- **Dashboard**: Command Center -> incident drill-down with evidence chain, entity graph, AI investigation, linked chargebacks, policy comparison; a separate Chargebacks section

## Architecture

```
Synthetic data generator -> 3 intelligence engines -> fusion -> loss events
-> counterfactual simulator -> FastAPI -> Next.js dashboard
```

Full diagram and design rationale in [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Project Structure

```
lossgraph/
├── backend/              # FastAPI backend (serves precomputed pipeline output)
├── frontend/             # Next.js dashboard
├── ml/                   # The three intelligence engines + fusion + loss events + counterfactual simulator
├── data/                 # Synthetic data generator + generated dataset
└── docs/                 # Architecture, evaluation, data model, API reference
```

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Graph**: NetworkX

### ML
- **Models**: LightGBM
- **Explainability**: SHAP
- **Time-series**: NumPy, Pandas, SciPy (custom Poisson rolling z-score)
- **AI Investigator**: Anthropic Claude Opus 5 (`client.messages.parse()`, Pydantic structured output), deterministic fallback

### Frontend
- **Framework**: Next.js (App Router) + TypeScript + Tailwind CSS
- **Visualization**: Cytoscape.js (entity graph)

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Run the intelligence pipeline

Generates the synthetic merchant ecosystem and runs all three engines +
fusion + loss event detection + counterfactual simulation. The backend
serves this output; it does not recompute it per request.

```bash
pip install -r backend/requirements.txt
make pipeline
```

### 2. Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 for the Command Center.

## Documentation

- [Quick Start](./QUICKSTART.md) -- get it running, with troubleshooting
- [Architecture](./docs/ARCHITECTURE.md) -- what was built, what was cut, and why
- [Evaluation](./docs/EVALUATION.md) -- held-out precision/recall, economic evaluation, stated limitations
- [Data Model](./docs/DATA_MODEL.md)
- [API Reference](./docs/API.md)
- [Roadmap](./ROADMAP.md) -- the real day-by-day build log
- [Data Generator Design](./data/README.md), [ML Engine Design](./ml/README.md) -- design decisions and bugs found/fixed along the way

## Development

No automated test suite yet -- correctness for the ML pipeline is
established by held-out evaluation instead (`docs/EVALUATION.md`), and the
frontend was verified with a real headless-browser pass rather than unit
tests. Both are gaps worth closing past the buildathon deadline, not
hidden.

```bash
# Frontend production build (type-checks + lints on build)
cd frontend && npm run build
```

## Project Principles

1. **Risk is not a score. Risk is a changing system.**
2. **Evidence-based decisions** - All claims traceable to underlying data
3. **Economic optimization** - Actions minimize expected merchant loss
4. **Robustness** - Conservative under legitimate-but-unusual behavior
5. **Transparency** - Complete audit trails and explainability

## Evaluation

Primary metric is expected loss reduction, not accuracy. Full held-out
precision/recall, economic evaluation, and honestly-stated limitations are
in [`docs/EVALUATION.md`](./docs/EVALUATION.md).

---

Built solo for the Razorpay AI Buildathon, Track 02: AI Risk Manager.
