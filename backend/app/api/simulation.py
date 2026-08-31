"""
Counterfactual policy simulation endpoints.

Serves the precomputed policy comparisons from ml/counterfactual.py -- see
app/data_access.py for why this reads offline pipeline output rather than
recomputing live.
"""

from fastapi import APIRouter, HTTPException

from app.data_access import PipelineNotRunError, get_event

router = APIRouter()


@router.get("/{event_id}/compare")
async def compare_policies(event_id: str):
    """Compare all candidate intervention policies for a risk event and
    return the economically-optimal recommendation (section 10-11)."""
    try:
        event = get_event(event_id)
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    cf = event["counterfactual"]
    allow = next(s for s in cf["simulations"] if s["action"] == "allow")
    best = next(s for s in cf["simulations"] if s["action"] == cf["recommended_action"])

    return {
        "event_id": event_id,
        "simulations": cf["simulations"],
        "recommended_action": cf["recommended_action"],
        "recommendation_reason": (
            f"Highest net economic benefit (Rs {best['net_benefit']:,.0f} vs Rs {allow['net_benefit']:,.0f} "
            f"for allowing everything) given this event's confidence and the merchant's cost parameters."
        ),
    }
