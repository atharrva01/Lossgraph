"""
Loss event incident endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RiskEvent, EventStatus

router = APIRouter()


class RiskEventResponse(BaseModel):
    """Response schema for risk event"""
    event_id: str
    event_type: str
    merchant_id: str
    status: str
    exposure: float
    confidence: float
    affected_entities: int
    affected_transactions: int
    detection_time: str
    recommended_action: str


class IncidentListResponse(BaseModel):
    """Response schema for incident list"""
    active_incidents: int
    total_exposure: float
    incidents: List[RiskEventResponse]


@router.get("")
async def get_incidents(
    merchant_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> IncidentListResponse:
    """
    Get all risk incidents for a merchant
    
    Returns active loss events with exposure and confidence
    """
    
    query = db.query(RiskEvent).filter(RiskEvent.merchant_id == merchant_id)
    
    if status:
        query = query.filter(RiskEvent.status == status)
    else:
        # Default to active incidents
        query = query.filter(
            RiskEvent.status.in_([
                EventStatus.DETECTED.value,
                EventStatus.INVESTIGATING.value,
                EventStatus.CONFIRMED.value
            ])
        )
    
    incidents = query.all()
    
    return IncidentListResponse(
        active_incidents=len(incidents),
        total_exposure=sum(inc.exposure for inc in incidents),
        incidents=[
            RiskEventResponse(
                event_id=inc.event_id,
                event_type=inc.event_type.value,
                merchant_id=inc.merchant_id,
                status=inc.status.value,
                exposure=inc.exposure,
                confidence=inc.confidence,
                affected_entities=inc.affected_entity_count,
                affected_transactions=inc.affected_transaction_count,
                detection_time=inc.detection_time.isoformat(),
                recommended_action=inc.recommended_action.value
            )
            for inc in incidents
        ]
    )


@router.get("/{event_id}")
async def get_incident_details(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a risk event"""
    
    event = db.query(RiskEvent).filter(RiskEvent.event_id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "merchant_id": event.merchant_id,
        "status": event.status.value,
        "exposure": event.exposure,
        "confidence": event.confidence,
        "affected_entities": event.affected_entity_count,
        "affected_transactions": event.affected_transaction_count,
        "detection_time": event.detection_time.isoformat(),
        "start_time": event.start_time.isoformat(),
        "recommended_action": event.recommended_action.value,
        "root_cause": event.root_cause,
        "evidence": event.evidence,
        "timeline": event.timeline
    }


@router.patch("/{event_id}/status")
async def update_incident_status(
    event_id: str,
    new_status: str,
    db: Session = Depends(get_db)
):
    """Update the status of an incident"""
    
    event = db.query(RiskEvent).filter(RiskEvent.event_id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    try:
        event.status = EventStatus[new_status.upper()]
        db.commit()
        return {"event_id": event_id, "new_status": event.status.value}
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
