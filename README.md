# LossGraph

**AI Risk Manager for Merchant Loss Intelligence**

Don't just score risky transactions. Understand how losses form, spread, and how to stop them.

## Overview

LossGraph is an AI-powered merchant risk intelligence system that detects, investigates and responds to emerging loss events across transactions, returns, refunds, chargebacks and coordinated abuse.

Unlike conventional fraud models that assign a risk score to individual transactions, LossGraph treats merchant risk as a **temporal, relational and evolving phenomenon**, building a continuously updated **Merchant Risk Graph** that connects transactions, customers, orders, devices, addresses, payment instruments, products, returns, refunds, and chargebacks.

## Key Features

- **Transaction Intelligence**: Real-time risk scoring of individual transactions
- **Network Intelligence**: Detection of coordinated abuse patterns across connected entities
- **Temporal Intelligence**: Identification of emerging loss events and unusual acceleration patterns
- **Counterfactual Reasoning**: Simulation of intervention strategies and economic impact analysis
- **Evidence-Grounded Explanations**: Complete audit trails and risk event genomes
- **Chargeback Responder**: Automated evidence generation for dispute responses

## Architecture

```
Transaction Stream
    ↓
[Transaction Model] [Time-Series Engine] [Graph Engine]
    ↓
    Loss Event Detection
    ↓
    Causal Investigation
    ↓
    Counterfactual Analysis
    ↓
    Action Optimization
    ↓
    Merchant Intervention
```

## Project Structure

```
lossgraph/
├── backend/              # FastAPI backend service
├── frontend/             # React frontend dashboard
├── ml/                   # Machine learning models
├── data/                 # Data generation and synthetic datasets
├── docs/                 # Documentation
└── tests/                # Test suite
```

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Graph**: NetworkX (with optional Neo4j)

### ML
- **Models**: LightGBM, XGBoost
- **Features**: scikit-learn, SHAP
- **Time-Series**: NumPy, Pandas, SciPy

### Frontend
- **Framework**: React/Next.js
- **Visualization**: Plotly, D3.js, Cytoscape.js

### Tools
- **ML Experiments**: MLflow
- **API Docs**: FastAPI (Swagger/OpenAPI)

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

- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Data Model](./docs/DATA_MODEL.md)
- [API Reference](./docs/API.md)
- [ML Models](./docs/ML_MODELS.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Building for Production

```bash
# Backend
cd backend
python -m pip install -r requirements.txt
# Use production ASGI server like Gunicorn

# Frontend
cd frontend
npm run build
```

## Project Principles

1. **Risk is not a score. Risk is a changing system.**
2. **Evidence-based decisions** - All claims traceable to underlying data
3. **Economic optimization** - Actions minimize expected merchant loss
4. **Robustness** - Conservative under legitimate-but-unusual behavior
5. **Transparency** - Complete audit trails and explainability

## Evaluation Metrics

Primary metrics:
- **Expected Loss Reduction**: How much loss prevented while preserving legitimate commerce
- **Detection Precision/Recall**: Quality of risk identification
- **Detection Latency**: Time to identify emerging loss events
- **False Positive Cost**: Impact on legitimate transactions

## License

[Add appropriate license]

## Contributing

[Add contribution guidelines]

## Contact

[Add contact information]
