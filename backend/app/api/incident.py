"""
Loss event incident endpoints.

Serves Risk Event Genome objects (evidence chain, exposure, counterfactual
recommendation) produced by the offline ml/ pipeline -- see
app/data_access.py for why this reads precomputed artifacts rather than
querying a live DB.
"""

from fastapi import APIRouter, HTTPException, Query

from app.data_access import (
    PipelineNotRunError, chargeback_cases_for_event, command_center_summary,
    engine_breakdown_for_event, get_event, graph_for_event, load_events, merchant_name,
)

router = APIRouter()


def _event_summary(e: dict) -> dict:
    return {
        "event_id": e["event_id"],
        "source": e["source"],
        "event_type": e["event_type"],
        "merchant_id": e["merchant_id"],
        "merchant_name": merchant_name(e["merchant_id"]),
        "start_time": e["start_time"],
        "detection_time": e["detection_time"],
        "confidence": e["confidence"],
        "exposure_estimate": e["exposure_estimate"],
        "affected_transaction_count": e["affected_transaction_count"],
        "affected_customer_count": e["affected_customer_count"],
        "primary_driver": e["primary_driver"],
        "recommended_action": e["counterfactual"]["recommended_action"],
    }


@router.get("")
async def get_incidents(merchant_id: str = Query(default="ALL")):
    """Command Center: summary metrics + the incident list, optionally
    scoped to one merchant."""
    try:
        events = load_events()
        summary = command_center_summary(merchant_id)
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if merchant_id != "ALL":
        events = [e for e in events if e["merchant_id"] == merchant_id]
    events = sorted(events, key=lambda e: e["exposure_estimate"], reverse=True)

    return {**summary, "incidents": [_event_summary(e) for e in events]}


@router.get("/{event_id}")
async def get_incident_details(event_id: str):
    """Full Risk Event Genome: evidence chain, ground-truth cross-check
    (evaluation-only -- a real deployment wouldn't have this), and the
    counterfactual policy comparison."""
    try:
        event = get_event(event_id)
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    linked_chargebacks = [
        {"case_id": c["case_id"], "reason_code": c["reason_code"], "recommendation": c["recommendation"],
         "amount": c["amount"]}
        for c in chargeback_cases_for_event(event_id)
    ]
    return {
        **event,
        "merchant_name": merchant_name(event["merchant_id"]),
        "linked_chargebacks": linked_chargebacks,
        "engine_breakdown": engine_breakdown_for_event(event),
    }


@router.get("/{event_id}/graph")
async def get_incident_graph(event_id: str):
    """Cytoscape-ready subgraph for a cluster event. Temporal events (no
    qualifying shared-entity cluster) return an empty graph by design."""
    try:
        event = get_event(event_id)
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return graph_for_event(event)
