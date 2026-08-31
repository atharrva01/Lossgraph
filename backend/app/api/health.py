"""
Health check endpoints
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LossGraph"
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancers"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }
