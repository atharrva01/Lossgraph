"""
Chargeback evidence and response endpoints.

Serves the precomputed cases from ml/chargeback_responder.py -- see
app/data_access.py for why this reads offline pipeline output rather than
recomputing live. Cases are scoped to the test split (see
ml/chargeback_responder.py for why), same as every other held-out number
in this repo.
"""

from fastapi import APIRouter, HTTPException, Query

from app.data_access import PipelineNotRunError, get_chargeback_case, load_chargeback_cases, merchant_name

router = APIRouter()


def _case_summary(c: dict) -> dict:
    return {
        "case_id": c["case_id"],
        "transaction_id": c["transaction_id"],
        "merchant_id": c["merchant_id"],
        "merchant_name": merchant_name(c["merchant_id"]),
        "amount": c["amount"],
        "reason_code": c["reason_code"],
        "disputed_at": c["disputed_at"],
        "recommendation": c["recommendation"],
        "evidence_completeness": c["evidence_completeness"],
        "has_contradictions": len(c["contradictions"]) > 0,
        "linked_loss_event": c["linked_loss_event"],
    }


@router.get("")
async def list_chargebacks(recommendation: str = Query(default="ALL")):
    """List all chargeback cases, optionally filtered by recommendation
    (CONTEST / ACCEPT / ESCALATE)."""
    try:
        cases = load_chargeback_cases()
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if recommendation != "ALL":
        cases = [c for c in cases if c["recommendation"] == recommendation.upper()]

    counts = {}
    for c in load_chargeback_cases():
        counts[c["recommendation"]] = counts.get(c["recommendation"], 0) + 1

    return {
        "total_cases": len(load_chargeback_cases()),
        "recommendation_counts": counts,
        "cases": [_case_summary(c) for c in cases],
    }


@router.get("/{case_id}")
async def get_case_detail(case_id: str):
    """Full case file: evidence checklist, contradictions, recommendation
    reasoning, linked Loss Event (if any), and the response draft."""
    try:
        case = get_chargeback_case(case_id)
    except PipelineNotRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if case is None:
        raise HTTPException(status_code=404, detail="Chargeback case not found")

    return {**case, "merchant_name": merchant_name(case["merchant_id"])}
