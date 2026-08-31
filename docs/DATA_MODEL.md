# LossGraph Data Model

## Overview

The LossGraph data model represents the complete ecosystem of merchant payment transactions, entities, relationships, and risk events. It is designed to support temporal graph analysis, anomaly detection, and counterfactual reasoning.

## Core Tables

### Merchants

```sql
CREATE TABLE merchants (
  id INTEGER PRIMARY KEY,
  merchant_id VARCHAR UNIQUE,
  name VARCHAR,
  created_at TIMESTAMP,
  risk_tolerance VARCHAR,  -- conservative, moderate, aggressive
  false_positive_cost FLOAT,
  verification_cost FLOAT
);
```

Represents a payment processor merchant account.

---

### Customers

```sql
CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  customer_id VARCHAR UNIQUE,
  merchant_id VARCHAR,
  created_at TIMESTAMP,
  transaction_count INTEGER,
  return_count INTEGER,
  refund_count INTEGER,
  chargeback_count INTEGER,
  lifetime_value FLOAT,
  risk_score FLOAT
);
```

Represents a customer with behavioral aggregates.

---

### Transactions

```sql
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY,
  transaction_id VARCHAR UNIQUE,
  merchant_id VARCHAR FK,
  customer_id VARCHAR FK,
  amount FLOAT,
  timestamp TIMESTAMP,
  payment_method VARCHAR,
  device_id VARCHAR,
  address_id VARCHAR,
  product_ids JSON,
  status VARCHAR,  -- approved, declined, pending, flagged, held
  risk_score FLOAT,
  expected_loss FLOAT
);
```

Represents individual payment transactions with risk scores.

**Indexes**: `(merchant_id, timestamp)`, `(customer_id)`, `(device_id)`, `(address_id)`

---

### Entities

```sql
CREATE TABLE entities (
  id INTEGER PRIMARY KEY,
  entity_id VARCHAR,
  entity_type VARCHAR,  -- device, address, payment_fingerprint, product
  first_seen TIMESTAMP,
  last_seen TIMESTAMP,
  risk_score FLOAT,
  associated_customer_id INTEGER FK,
  merchant_id VARCHAR,
  metadata JSON
);
```

Generic representation of any entity that can participate in relationships (devices, addresses, payment fingerprints, products, etc.).

**Indexes**: `(entity_id, entity_type)`, `(merchant_id)`, `(entity_type)`

---

### Relationships

```sql
CREATE TABLE relationships (
  id INTEGER PRIMARY KEY,
  source_id INTEGER FK,  -- entities.id
  target_id INTEGER FK,  -- entities.id
  relationship_type VARCHAR,  -- shared_device, shared_address, etc.
  first_seen TIMESTAMP,
  last_seen TIMESTAMP,
  frequency INTEGER,
  confidence FLOAT,
  merchant_id VARCHAR
);
```

Represents directed edges in the merchant risk graph with temporal metadata.

**Indexes**: `(source_id, target_id)`, `(merchant_id, relationship_type)`

**Key Insight**: Temporal edges allow distinguishing coordinated activity (multiple shared in 48 hours) from coincidental overlap (shared device 6 months apart).

---

### Risk Events

```sql
CREATE TABLE risk_events (
  id INTEGER PRIMARY KEY,
  event_id VARCHAR UNIQUE,
  merchant_id VARCHAR FK,
  event_type VARCHAR,  -- coordinated_return, fraud_spike, etc.
  start_time TIMESTAMP,
  detection_time TIMESTAMP,
  exposure FLOAT,
  confidence FLOAT,
  status VARCHAR,  -- detected, investigating, confirmed, dismissed, actioned, resolved
  affected_entity_count INTEGER,
  affected_transaction_count INTEGER,
  evidence JSON,
  recommended_action VARCHAR,
  root_cause TEXT,
  timeline JSON
);
```

Represents detected loss events with full investigation state and timeline.

**Indexes**: `(merchant_id, status)`, `(detection_time)`, `(event_type)`

---

### Counterfactuals

```sql
CREATE TABLE counterfactuals (
  id INTEGER PRIMARY KEY,
  risk_event_id INTEGER FK,
  action VARCHAR,  -- allow, monitor, verify, hold, block
  expected_loss FLOAT,
  loss_prevented FLOAT,
  legitimate_orders_affected INTEGER,
  operational_cost FLOAT,
  net_benefit FLOAT,
  created_at TIMESTAMP
);
```

Stores simulated policy outcomes for a given risk event.

Multiple counterfactuals per event allow comparison of intervention strategies.

---

## Relationships (Foreign Keys)

```
Merchant ──1 ──── ∞── Transaction
Merchant ──1 ──── ∞── RiskEvent

Customer ──1 ──── ∞── Transaction
Customer ──1 ──── ∞── Entity (associated_customer)

Entity ──1 ──── ∞── Relationship (source)
Entity ──1 ──── ∞── Relationship (target)

RiskEvent ──1 ──── ∞── Counterfactual
RiskEvent ──∞ ──── ∞── Transaction (junction table)
```

---

## Temporal Design Decisions

### Why Temporal Edges Matter

A customer using the same device 6 months ago is NOT equivalent to:
- 14 accounts using the same device within 48 hours

Therefore, every relationship includes:

```json
{
  "relationship_type": "shared_device",
  "first_seen": "2026-08-15 10:32:00",
  "last_seen": "2026-08-17 14:22:00",
  "frequency": 12,
  "confidence": 0.94
}
```

**Benefits**:
- Detect acceleration (recency bias)
- Distinguish coincidence from coordination
- Enable temporal graph algorithms
- Support "risk propagation" with decay

---

## Indexing Strategy

### High-Priority Indexes

1. **Transaction queries** (most frequent)
   - `(merchant_id, timestamp)`
   - `(customer_id)`
   - `(device_id, timestamp)`

2. **Relationship queries** (graph traversal)
   - `(source_id, target_id)`
   - `(merchant_id, relationship_type)`

3. **Risk event queries** (dashboard)
   - `(merchant_id, status)`
   - `(detection_time DESC)`

### Storage Optimization

- Use JSON columns for flexible metadata
- Denormalize frequently-queried aggregates (transaction_count, risk_score)
- Archive old transactions (> 2 years) to cold storage
- Partition by merchant_id for scalability

---

## Query Patterns

### Find all customers connected to a device

```sql
SELECT DISTINCT c.customer_id
FROM relationships r
JOIN entities source ON r.source_id = source.id
JOIN entities target ON r.target_id = target.id
JOIN customers c ON target.associated_customer_id = c.id
WHERE source.entity_id = 'DEVICE_123'
  AND r.relationship_type = 'shared_device'
  AND r.last_seen > NOW() - INTERVAL '7 days'
ORDER BY r.confidence DESC;
```

### Find transactions in a potential abuse cluster

```sql
SELECT t.transaction_id, t.amount, t.timestamp
FROM transactions t
WHERE t.merchant_id = 'MERCHANT_001'
  AND t.customer_id IN (
    -- Get cluster members
    SELECT DISTINCT c.customer_id
    FROM relationships r
    JOIN entities e ON (r.source_id = e.id OR r.target_id = e.id)
    JOIN customers c ON e.associated_customer_id = c.id
    WHERE e.entity_type = 'device'
      AND r.relationship_type = 'shared_device'
      AND r.last_seen > NOW() - INTERVAL '3 days'
  )
ORDER BY t.timestamp DESC;
```

### Calculate anomaly metrics

```sql
SELECT 
  DATE_TRUNC('hour', timestamp) as hour,
  COUNT(*) as transaction_count,
  SUM(amount) as total_amount,
  AVG(risk_score) as avg_risk,
  COUNT(CASE WHEN status = 'returned' THEN 1 END)::float / COUNT(*) as return_rate
FROM transactions
WHERE merchant_id = 'MERCHANT_001'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY hour
ORDER BY hour DESC;
```

---

## Cold Start Handling

For new merchants and customers without historical data:

```json
{
  "customer_prior": {
    "return_rate": 0.021,  // Global baseline
    "chargeback_rate": 0.008,
    "transaction_value": 2500,
    "confidence": 0.3  // Low confidence due to cold start
  },
  "merchant_prior": {
    "fraud_rate": 0.015,
    "return_rate": 0.025,
    "operational_cost": 450,
    "confidence": 0.4
  }
}
```

---

## Data Retention Policy

| Table | Retention | Rationale |
|-------|-----------|-----------|
| Transactions | 2 years | Chargebacks up to 180 days; disputes possible for 2 years |
| Relationships | 1 year | Detect seasonal patterns; coordinate abuse recurrence |
| RiskEvents | Indefinite | Complete audit trail of merchant risk history |
| Counterfactuals | 6 months | Learning from simulations; trend analysis |
| Customer aggregates | Indefinite | Lifetime value tracking |

---

## Scaling Considerations

### Partitioning

Partition transactions by merchant_id for horizontal scalability:

```sql
CREATE TABLE transactions_MERCHANT_001 PARTITION OF transactions
  FOR VALUES IN ('MERCHANT_001');
```

### Sharding

For multi-tenant deployments, shard by merchant_id to distribute load.

### Denormalization

Cache frequently-queried aggregates:

```json
{
  "customer_id": "CUST_123",
  "cached_metrics": {
    "transaction_count": 47,
    "return_count": 3,
    "lifetime_value": 125000,
    "last_updated": "2026-08-31T10:15:00Z"
  }
}
```

Update on transaction completion to maintain consistency.

---

## Audit Trail

Every risk event decision includes:

```json
{
  "timestamp": "2026-08-31T10:32:15Z",
  "model_version": "v2.1.4",
  "input_hash": "abc123...",
  "risk_score": 0.81,
  "graph_score": 0.72,
  "expected_loss": 3210,
  "selected_action": "verify",
  "alternative_actions": ["monitor", "hold"],
  "decision_reason": "Optimal net benefit with minimal false positive impact",
  "evidence_ids": ["E1", "E2", "E3"],
  "policy_version": "conservative",
  "actor": "system|merchant_admin",
  "outcome": null  // Populated after event resolves
}
```

Enables complete reconstruction and model improvement.
