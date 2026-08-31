"""
Entity investigation endpoints (devices, addresses, payment fingerprints, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Entity, Relationship

router = APIRouter()


class EntityResponse(BaseModel):
    """Response schema for entity information"""
    entity_id: str
    entity_type: str
    risk_score: float
    first_seen: str
    last_seen: str
    connected_entities: int
    metadata: dict


class EntityRelationshipResponse(BaseModel):
    """Response schema for entity relationships"""
    source_id: str
    target_id: str
    relationship_type: str
    frequency: int
    confidence: float
    first_seen: str
    last_seen: str


@router.get("/{entity_id}")
async def get_entity_details(
    entity_id: str,
    db: Session = Depends(get_db)
) -> EntityResponse:
    """
    Get detailed information about an entity (device, address, payment fingerprint)
    
    Returns entity risk profile and connected relationships
    """
    
    entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Get connected entities count
    connected = db.query(Relationship).filter(
        (Relationship.source_id == entity.id) | (Relationship.target_id == entity.id)
    ).count()
    
    return EntityResponse(
        entity_id=entity.entity_id,
        entity_type=entity.entity_type,
        risk_score=entity.risk_score,
        first_seen=entity.first_seen.isoformat(),
        last_seen=entity.last_seen.isoformat(),
        connected_entities=connected,
        metadata=entity.entity_metadata
    )


@router.get("/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get all relationships for an entity"""
    
    entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    relationships = db.query(Relationship).filter(
        (Relationship.source_id == entity.id) | (Relationship.target_id == entity.id)
    ).all()
    
    return {
        "entity_id": entity_id,
        "relationship_count": len(relationships),
        "relationships": [
            {
                "source_id": r.source.entity_id,
                "target_id": r.target.entity_id,
                "relationship_type": r.relationship_type,
                "frequency": r.frequency,
                "confidence": r.confidence
            }
            for r in relationships
        ]
    }
