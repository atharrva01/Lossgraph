"""
Transaction risk scoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Transaction, Customer, Merchant

router = APIRouter()


class TransactionRequest(BaseModel):
    """Request schema for transaction scoring"""
    transaction_id: str
    merchant_id: str
    customer_id: str
    amount: float
    payment_method: str
    device_id: str
    address_id: str
    product_ids: Optional[list] = []


class TransactionResponse(BaseModel):
    """Response schema for transaction scoring"""
    transaction_id: str
    risk_score: float
    expected_loss: float
    decision: str
    reasons: list
    connected_risk: float
    recommended_action: str


@router.post("/score")
async def score_transaction(
    request: TransactionRequest,
    db: Session = Depends(get_db)
) -> TransactionResponse:
    """
    Score a transaction for risk
    
    Returns:
    - risk_score: 0-1 probability of loss
    - expected_loss: Estimated financial loss
    - decision: ALLOW, MONITOR, VERIFY, HOLD, BLOCK
    - connected_risk: Risk from related entities
    """
    
    # TODO: Implement transaction risk model
    # For now, return placeholder response
    
    return TransactionResponse(
        transaction_id=request.transaction_id,
        risk_score=0.35,
        expected_loss=150.0,
        decision="MONITOR",
        reasons=["Higher than average transaction value", "New customer"],
        connected_risk=0.22,
        recommended_action="MONITOR"
    )


@router.get("/{transaction_id}")
async def get_transaction_details(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed transaction information"""
    
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "transaction_id": transaction.transaction_id,
        "merchant_id": transaction.merchant_id,
        "customer_id": transaction.customer_id,
        "amount": transaction.amount,
        "timestamp": transaction.timestamp,
        "risk_score": transaction.risk_score,
        "expected_loss": transaction.expected_loss
    }
