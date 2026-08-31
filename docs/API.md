# LossGraph API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently uses no authentication. In production, implement:
- JWT bearer tokens
- API key authentication
- OAuth2 with scopes

## Response Format

All endpoints return JSON. Standard response structure:

### Success Response (2xx)
```json
{
  "data": { /* Response body */ },
  "status": "success",
  "timestamp": "2026-08-31T10:32:15Z"
}
```

### Error Response (4xx, 5xx)
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2026-08-31T10:32:15Z"
}
```

---

## Endpoints

### Health & Status

#### GET /health

Check if the service is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-08-31T10:32:15Z",
  "service": "LossGraph"
}
```

#### GET /health/ready

Check if the service is ready to handle requests (database connectivity, etc.).

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2026-08-31T10:32:15Z"
}
```

---

### Transaction Risk Scoring

#### POST /risk/transaction/score

Score a transaction for fraud/loss risk.

**Request Body:**
```json
{
  "transaction_id": "TXN_123456",
  "merchant_id": "MERCH_001",
  "customer_id": "CUST_789",
  "amount": 4500.00,
  "payment_method": "card",
  "device_id": "DEVICE_XYZ",
  "address_id": "ADDR_ABC",
  "product_ids": ["SKU_001", "SKU_002"]
}
```

**Response:**
```json
{
  "transaction_id": "TXN_123456",
  "risk_score": 0.35,
  "expected_loss": 150.00,
  "decision": "MONITOR",
  "reasons": [
    "Higher than average transaction value",
    "New customer"
  ],
  "connected_risk": 0.22,
  "recommended_action": "MONITOR"
}
```

**Risk Scores:**
- 0.00 - 0.30: LOW
- 0.30 - 0.60: MEDIUM
- 0.60 - 0.80: HIGH
- 0.80 - 1.00: CRITICAL

**Decisions:**
- `ALLOW`: Process normally
- `MONITOR`: Track for patterns
- `VERIFY`: Request additional verification
- `HOLD`: Temporarily hold pending review
- `BLOCK`: Decline transaction

---

#### GET /risk/transaction/{transaction_id}

Get detailed information about a specific transaction.

**Response:**
```json
{
  "transaction_id": "TXN_123456",
  "merchant_id": "MERCH_001",
  "customer_id": "CUST_789",
  "amount": 4500.00,
  "timestamp": "2026-08-31T10:32:15Z",
  "risk_score": 0.35,
  "expected_loss": 150.00
}
```

---

### Entity Investigation

#### GET /risk/entity/{entity_id}

Get detailed information about an entity (device, address, payment fingerprint, etc.).

**Query Parameters:**
- `type` (optional): Filter by entity type (device, address, payment_fingerprint, product)

**Response:**
```json
{
  "entity_id": "DEVICE_XYZ",
  "entity_type": "device",
  "risk_score": 0.45,
  "first_seen": "2026-08-15T08:00:00Z",
  "last_seen": "2026-08-31T10:32:15Z",
  "connected_entities": 12,
  "metadata": {
    "device_fingerprint": "abc123def456",
    "user_agent": "Mozilla/5.0..."
  }
}
```

#### GET /risk/entity/{entity_id}/relationships

Get all relationships for an entity.

**Response:**
```json
{
  "entity_id": "DEVICE_XYZ",
  "relationship_count": 5,
  "relationships": [
    {
      "source_id": "CUST_001",
      "target_id": "DEVICE_XYZ",
      "relationship_type": "used_device",
      "frequency": 3,
      "confidence": 0.92,
      "first_seen": "2026-08-29T14:00:00Z",
      "last_seen": "2026-08-31T10:32:15Z"
    }
  ]
}
```

---

### Risk Incident Management

#### GET /risk/incidents

Get all risk incidents for a merchant.

**Query Parameters:**
- `merchant_id` (required): Merchant identifier
- `status` (optional): Filter by status (detected, investigating, confirmed, dismissed, actioned, resolved)

**Response:**
```json
{
  "active_incidents": 4,
  "total_exposure": 842000,
  "incidents": [
    {
      "event_id": "RE-2026-00871",
      "event_type": "coordinated_return_abuse",
      "merchant_id": "MERCH_001",
      "status": "investigating",
      "exposure": 482000,
      "confidence": 0.91,
      "affected_entities": 94,
      "affected_transactions": 173,
      "detection_time": "2026-08-31T14:32:00Z",
      "recommended_action": "VERIFY"
    }
  ]
}
```

#### GET /risk/incidents/{event_id}

Get detailed information about a specific risk event.

**Response:**
```json
{
  "event_id": "RE-2026-00871",
  "event_type": "coordinated_return_abuse",
  "merchant_id": "MERCH_001",
  "status": "investigating",
  "exposure": 482000,
  "confidence": 0.91,
  "affected_entities": 94,
  "affected_transactions": 173,
  "detection_time": "2026-08-31T14:32:00Z",
  "start_time": "2026-08-31T13:20:00Z",
  "recommended_action": "VERIFY",
  "root_cause": "Return rate spike on high-value SKUs with shared device cluster",
  "evidence": {
    "return_rate_increase": 4.1,
    "device_sharing_increase": 3.2,
    "refund_velocity_increase": 2.7
  },
  "timeline": [
    {
      "time": "2026-08-31T13:20:00Z",
      "event": "Anomaly detected in return rate"
    },
    {
      "time": "2026-08-31T14:32:00Z",
      "event": "Risk event created with cluster analysis"
    }
  ]
}
```

#### PATCH /risk/incidents/{event_id}/status

Update the status of a risk event.

**Request Body:**
```json
{
  "new_status": "confirmed"
}
```

**Valid Statuses:**
- `DETECTED`: Initial detection
- `INVESTIGATING`: Under investigation
- `CONFIRMED`: Confirmed loss event
- `DISMISSED`: False positive
- `ACTIONED`: Action taken
- `RESOLVED`: Event resolved

**Response:**
```json
{
  "event_id": "RE-2026-00871",
  "new_status": "confirmed"
}
```

---

### Counterfactual Policy Simulation

#### POST /risk/simulate/{event_id}/policy

Simulate a single intervention policy for a risk event.

**Request Body:**
```json
{
  "action": "VERIFY"
}
```

**Valid Actions:**
- `ALLOW`: No intervention
- `MONITOR`: Track transactions
- `VERIFY`: Request additional verification
- `HOLD`: Temporarily hold transactions
- `BLOCK`: Decline transactions

**Response:**
```json
{
  "action": "VERIFY",
  "expected_loss": 1200.00,
  "loss_prevented": 3600.00,
  "legitimate_orders_affected": 6,
  "operational_cost": 240.00,
  "net_benefit": 3360.00
}
```

#### GET /risk/simulate/{event_id}/compare

Compare multiple intervention policies to find optimal action.

**Response:**
```json
{
  "event_id": "RE-2026-00871",
  "simulations": [
    {
      "action": "ALLOW",
      "expected_loss": 4800.00,
      "loss_prevented": 0.00,
      "legitimate_orders_affected": 0,
      "operational_cost": 0.00,
      "net_benefit": -4800.00
    },
    {
      "action": "VERIFY",
      "expected_loss": 1200.00,
      "loss_prevented": 3600.00,
      "legitimate_orders_affected": 6,
      "operational_cost": 240.00,
      "net_benefit": 3360.00
    },
    {
      "action": "BLOCK",
      "expected_loss": 600.00,
      "loss_prevented": 4200.00,
      "legitimate_orders_affected": 38,
      "operational_cost": 0.00,
      "net_benefit": 4200.00
    }
  ],
  "recommended_action": "VERIFY",
  "recommendation_reason": "Optimal balance between loss prevention and customer impact"
}
```

---

### Chargeback Management

#### POST /risk/chargeback/{chargeback_id}/evidence

Generate an evidence package for a chargeback dispute response.

**Request Body:**
```json
{
  "chargeback_id": "CB-2026-001234",
  "transaction_id": "TXN_123456",
  "reason_code": "08"  // Non-receipt
}
```

**Reason Codes:**
- `08`: Non-receipt
- `04`: Fraudulent
- `34`: Duplicate
- `53`: Not as described
- `99`: Other

**Response:**
```json
{
  "chargeback_id": "CB-2026-001234",
  "transaction_id": "TXN_123456",
  "reason_code": "08",
  "evidence_items": [
    {
      "type": "invoice",
      "description": "Order invoice present",
      "status": "present",
      "confidence": 1.0
    },
    {
      "type": "delivery_confirmation",
      "description": "Delivery confirmed",
      "status": "present",
      "confidence": 0.95
    },
    {
      "type": "customer_history",
      "description": "Customer has 4 previous successful deliveries",
      "status": "present",
      "confidence": 0.9
    }
  ],
  "recommendation": "CONTEST",
  "evidence_completeness": 0.94,
  "confidence": 0.91
}
```

#### GET /risk/chargeback/{chargeback_id}/context

Get full context for a chargeback including transaction and risk history.

**Query Parameters:**
- `transaction_id` (required): Transaction ID

**Response:**
```json
{
  "chargeback_id": "CB-2026-001234",
  "transaction": {
    "transaction_id": "TXN_123456",
    "amount": 4500.00,
    "timestamp": "2026-08-25T10:32:15Z",
    "customer_id": "CUST_789",
    "payment_method": "card"
  },
  "customer_history": {
    "total_transactions": 47,
    "successful_orders": 44,
    "return_count": 3
  },
  "related_incidents": [
    {
      "event_id": "RE-2026-00871",
      "event_type": "coordinated_return_abuse",
      "status": "investigating",
      "confidence": 0.91
    }
  ]
}
```

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate ID) |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Rate Limiting

**Limits** (per API key, per minute):
- Default: 1000 requests/minute
- Burst: 100 requests/second

**Headers:**
- `X-RateLimit-Limit`: Maximum requests in window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Pagination

Endpoints returning lists support pagination:

**Query Parameters:**
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

**Response Headers:**
- `X-Total-Count`: Total number of items
- `X-Page-Count`: Total number of pages

---

## Webhooks

(Future: Implement webhook notifications for risk events)

```
POST /webhooks/risk-events
POST /webhooks/chargebacks
```

---

## SDK Examples

### Python
```python
from lossgraph import LossGraphClient

client = LossGraphClient(base_url="http://localhost:8000/api/v1")

# Score a transaction
result = client.risk.score_transaction(
    transaction_id="TXN_123456",
    merchant_id="MERCH_001",
    customer_id="CUST_789",
    amount=4500.00,
    payment_method="card",
    device_id="DEVICE_XYZ",
    address_id="ADDR_ABC"
)
print(f"Risk Score: {result.risk_score}")

# Get incidents
incidents = client.risk.get_incidents(merchant_id="MERCH_001")
print(f"Active Incidents: {incidents.active_incidents}")
```

### JavaScript/TypeScript
```typescript
import { LossGraphClient } from 'lossgraph-js';

const client = new LossGraphClient({
  baseURL: 'http://localhost:8000/api/v1'
});

const result = await client.risk.scoreTransaction({
  transaction_id: 'TXN_123456',
  merchant_id: 'MERCH_001',
  customer_id: 'CUST_789',
  amount: 4500.00,
  payment_method: 'card',
  device_id: 'DEVICE_XYZ',
  address_id: 'ADDR_ABC'
});

console.log(`Risk Score: ${result.risk_score}`);
```
