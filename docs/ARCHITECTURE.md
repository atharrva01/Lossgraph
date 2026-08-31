# LossGraph Architecture

## System Overview

LossGraph is built as a layered system consisting of five major intelligence engines that work together to detect, analyze, and respond to merchant loss events.

### Architecture Diagram

```
                 ┌─────────────────────┐
                 │      MERCHANT        │
                 └──────────┬──────────┘
                            │
                  Payment / Order Events
                            │
                            ▼
                ┌──────────────────────────┐
                │     EVENT INGESTION      │
                └────────────┬─────────────┘
                             │
            ┌────────────────┼──────────────────┐
            │                │                  │
            ▼                ▼                  ▼
     Transaction ML      Time-Series        Entity Graph
       Risk Model        Anomaly Engine         Engine
            │                │                  │
            └────────────────┼──────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   RISK FUSION       │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ LOSS EVENT ENGINE   │
                  └──────────┬──────────┘
                             │
               ┌─────────────┼──────────────┐
               │             │              │
               ▼             ▼              ▼
          Exposure       Evidence       Root Cause
           Engine          Chain         Analysis
               │             │              │
               └─────────────┼──────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ LLM INVESTIGATOR    │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ COUNTERFACTUAL      │
                  │ POLICY SIMULATOR    │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ ACTION OPTIMIZER    │
                  └──────────┬──────────┘
                             │
               ┌──────────────┼───────────────┐
               ▼              ▼               ▼
            MONITOR        VERIFY          HOLD/
                                            CONTEST
               │              │               │
               └──────────────┼───────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ OUTCOME / FEEDBACK  │
                   └──────────┬──────────┘
                              │
                              └────────→ Model updates
```

## Core Components

### 1. Transaction Risk Model (Engine 1)

**Purpose**: Predict fraud probability for individual transactions

**Inputs**:
- Transaction amount and time
- Customer history and behavior
- Payment method and device fingerprints
- Merchant and product characteristics

**Output**: `P(transaction_loss)` - Probability of loss

**Implementation**: LightGBM/XGBoost with SHAP explainability

---

### 2. Entity Behavior Models (Engine 2)

**Purpose**: Establish behavioral baselines for entities

**Monitored entities**:
- Customers
- Devices
- Addresses
- Payment fingerprints
- Products

**Metrics**:
- Return rate
- Refund velocity
- Chargeback frequency
- Anomaly score (vs. baseline)

---

### 3. Graph Risk Engine (Engine 3)

**Purpose**: Detect coordinated abuse patterns through relationship analysis

**Node types**:
- Merchant, Customer, Transaction, Order
- Device, Address, PaymentInstrument, Product
- Refund, Return, Chargeback

**Edge types**:
- PLACED (customer → transaction)
- USED_DEVICE, USED_ADDRESS, USED_PAYMENT
- BOUGHT_PRODUCT
- RETURNED, REFUNDED, DISPUTED

**Algorithms**:
- Connected components (identify clusters)
- Community detection (find coordinated groups)
- Temporal neighborhood analysis
- Suspicious subgraph scoring

---

### 4. Merchant Anomaly Engine (Engine 4)

**Purpose**: Detect sudden changes in merchant risk metrics

**Techniques**:
- EWMA (Exponential Weighted Moving Average)
- CUSUM (Cumulative Sum Control Chart)
- Rolling z-score
- Change-point detection
- Seasonal baseline normalization

**Monitored metrics**:
- Fraud rate, Return rate, Refund rate, Chargeback rate
- Average order value
- High-risk transaction percentage
- Cluster concentration

---

### 5. AI Investigation Layer (Engine 5)

**Purpose**: Generate grounded explanations and recommendations

**Input**: Structured outputs from deterministic/ML systems

**Output**:
- Incident summary
- Primary hypothesis
- Supporting and contradicting evidence
- Affected entities and exposure
- Recommended intervention with confidence
- Unknowns and data gaps

**Guardrails**:
- Cannot invent evidence
- Every claim must map to underlying data
- Cannot declare fraud independently
- Cannot execute financial actions without approval

---

## Loss Event Detection

A **Loss Event** is a statistically significant, potentially connected pattern of behavior that creates or is likely to create financial loss for a merchant.

### Detection Workflow

1. **Signal Collection**: Combine signals from all engines
2. **Change Detection**: Identify statistically unusual patterns
3. **Decomposition**: Answer WHERE, WHO, WHAT CHANGED
4. **Connection Analysis**: Find related entities and patterns
5. **Risk Event Genome**: Generate structured risk event profile

### Risk Event Genome

```json
{
  "event_id": "RE-2026-00871",
  "type": "coordinated_return_abuse",
  "confidence": 0.91,
  "exposure": 482000,
  "affected_orders": 173,
  "affected_customers": 61,
  "connected_entities": 94,
  "primary_driver": "SKU-8472",
  "secondary_signals": [
    "4.1× return-rate increase",
    "3.2× device-sharing increase",
    "2.7× refund velocity increase"
  ],
  "timeline": [
    {"time": "14:32", "event": "Detection"},
    {"time": "15:08", "event": "Cluster expanded to 17 entities"},
    {"time": "15:42", "event": "Exposure crosses ₹1L"}
  ]
}
```

---

## Counterfactual Analysis

For each detected loss event, simulate multiple intervention policies to determine optimal action.

### Simulation Metrics

- **Expected Loss**: Predicted loss without intervention
- **Loss Prevented**: Reduction in expected loss
- **Legitimate Orders Affected**: False positive cost
- **Operational Cost**: Cost of intervention (verification, investigation, etc.)
- **Net Benefit**: Loss prevented - false positive cost - operational cost

### Optimization Function

```
Choose action = argmin(Expected Economic Cost)
  where Expected Cost = 
    P(loss) × Loss Amount
    + P(false_positive) × FP Cost
    + Intervention Cost
```

---

## Data Model

### Core Entities

- **Merchant**: Payment processor account
- **Customer**: User making purchases
- **Transaction**: Individual payment event
- **Entity**: Generic reference (device, address, payment fingerprint)
- **Relationship**: Connections between entities (graph edges)
- **RiskEvent**: Detected loss event cluster
- **Counterfactual**: Simulated intervention outcome

### Temporal Awareness

All relationships and events include:
- `first_seen`: Initial occurrence
- `last_seen`: Most recent occurrence
- `frequency`: Number of times observed
- `confidence`: Statistical confidence in the relationship

---

## API Layer

The system exposes a RESTful API with endpoints for:

- **Transaction Scoring**: Real-time risk assessment
- **Entity Investigation**: Detailed entity risk profiles
- **Incident Management**: Loss event lifecycle
- **Simulation**: Policy comparison and optimization
- **Chargeback Response**: Evidence generation and dispute support

---

## Evaluation Framework

### Classification Metrics
- Precision, Recall, F1, PR-AUC, ROC-AUC

### Operational Metrics
- False-positive rate
- False-negative rate
- Intervention rate
- Fraud capture rate
- Detection latency

### Economic Metrics
- Gross loss
- Expected loss
- Prevented loss
- False-positive cost
- Intervention cost
- **Net economic benefit** (primary metric)

---

## Technology Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Language**: Python 3.9+

### ML
- **Models**: LightGBM, XGBoost
- **Explainability**: SHAP
- **Time-Series**: NumPy, Pandas, SciPy
- **Graph**: NetworkX

### Frontend
- **Framework**: React/Next.js
- **Visualization**: Plotly, D3.js, Cytoscape.js

### Deployment
- **Server**: Gunicorn + Uvicorn
- **Container**: Docker
- **Orchestration**: Kubernetes (optional)
