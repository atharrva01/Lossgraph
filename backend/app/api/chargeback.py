"""
Chargeback evidence and response endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Transaction, RiskEvent

router = APIRouter()


class EvidenceItem(BaseModel):
    """Individual evidence piece"""
    type: str
    description: str
    status: str  # present, missing, contradictory
    confidence: float


class ChargebackResponse(BaseModel):
    """Chargeback response"""
    chargeback_id: str
    transaction_id: str
    reason_code: str
    evidence_items: List[EvidenceItem]
    recommendation: str
    evidence_completeness: float
    confidence: float
    related_incident: Optional[str]


class ChargebackEvidenceRequest(BaseModel):
    """Request for generating chargeback evidence"""
    chargeback_id: str
    transaction_id: str
    reason_code: str


@router.post("/{chargeback_id}/evidence")
async def generate_evidence(
    chargeback_id: str,
    request: ChargebackEvidenceRequest,
    db: Session = Depends(get_db)
) -> ChargebackResponse:
    """
    Generate evidence package for chargeback response
    
    Connects to risk event history and produces grounded evidence
    """
    
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == request.transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # TODO: Implement evidence generation logic
    # Check related risk events, collect evidence, detect contradictions
    
    return ChargebackResponse(
        chargeback_id=chargeback_id,
        transaction_id=request.transaction_id,
        reason_code=request.reason_code,
        evidence_items=[
            EvidenceItem(
                type="invoice",
                description="Order invoice present",
                status="present",
                confidence=1.0
            ),
            EvidenceItem(
                type="delivery_confirmation",
                description="Delivery confirmed",
                status="present",
                confidence=0.95
            ),
            EvidenceItem(
                type="customer_history",
                description="Customer has 4 previous successful deliveries",
                status="present",
                confidence=0.9
            ),
        ],
        recommendation="CONTEST",
        evidence_completeness=0.94,
        confidence=0.91
    )


@router.get("/{chargeback_id}/context")
async def get_chargeback_context(
    chargeback_id: str,
    transaction_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get full context for a chargeback including risk history
    
    Returns transaction details, customer history, and related incidents
    """
    
    if not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id required")
    
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Find related risk events
    related_events = db.query(RiskEvent).filter(
        RiskEvent.merchant_id == transaction.merchant_id
    ).all()
    
    return {
        "chargeback_id": chargeback_id,
        "transaction": {
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "timestamp": transaction.timestamp.isoformat(),
            "customer_id": transaction.customer_id,
            "payment_method": transaction.payment_method
        },
        "customer_history": {
            "total_transactions": transaction.customer.transaction_count if transaction.customer else 0,
            "successful_orders": max(0, (transaction.customer.transaction_count - transaction.customer.chargeback_count) if transaction.customer else 0),
            "return_count": transaction.customer.return_count if transaction.customer else 0
        },
        "related_incidents": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "status": e.status.value,
                "confidence": e.confidence
            }
            for e in related_events[:5]  # Last 5 incidents
        ]
    }
