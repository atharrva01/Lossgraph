"""Merchant listing -- backs the dashboard's merchant selector."""

from fastapi import APIRouter, HTTPException

from app.data_access import PipelineNotRunError, load_events, load_merchants

router = APIRouter()


@router.get("")
async def list_merchants():
    try:
        merchants = load_merchants()
        events = load_events()
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    incident_counts = {}
    for e in events:
        incident_counts[e["merchant_id"]] = incident_counts.get(e["merchant_id"], 0) + 1

    return [
        {
            "merchant_id": row.merchant_id, "name": row.name, "category": row.category,
            "risk_tolerance": row.risk_tolerance, "incident_count": incident_counts.get(row.merchant_id, 0),
        }
        for row in merchants.itertuples(index=False)
    ]
