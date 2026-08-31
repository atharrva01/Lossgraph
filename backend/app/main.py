"""
LossGraph Backend - FastAPI Application

Main entry point for the AI Risk Manager for Merchant Loss Intelligence
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import routers
from app.api import transaction, entity, incident, simulation, chargeback, health

# Import database initialization
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    print("✅ LossGraph Backend Started")
    yield
    # Shutdown
    print("🛑 LossGraph Backend Shutdown")


# Initialize FastAPI app
app = FastAPI(
    title="LossGraph API",
    description="AI Risk Manager for Merchant Loss Intelligence",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(transaction.router, prefix="/api/v1/risk/transaction", tags=["Transaction"])
app.include_router(entity.router, prefix="/api/v1/risk/entity", tags=["Entity"])
app.include_router(incident.router, prefix="/api/v1/risk/incidents", tags=["Incident"])
app.include_router(simulation.router, prefix="/api/v1/risk/simulate", tags=["Simulation"])
app.include_router(chargeback.router, prefix="/api/v1/risk/chargeback", tags=["Chargeback"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LossGraph",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
