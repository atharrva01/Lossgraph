"""
Chargeback Responder + Evidence Contradiction Detector (PRD section 18-19).

For every disputed transaction, assembles the evidence a reason code
actually requires, checks for contradictions in the merchant's own data
before recommending anything, and links back to this same pipeline's own
loss-event detection -- so a transaction our own risk engine already
flagged with high confidence gets recommended for ACCEPT, not CONTEST,
even though "contest every chargeback" would look more aggressive. That
link (dispute -> Loss Event) is the payoff of building detection and
response in the same system instead of two disconnected tools.

Recommendation is entirely rule-based and deterministic; the optional LLM
call only drafts the prose response text from a recommendation and
evidence set that are already decided -- same division of labor as
investigator.py, and it reuses the same grounding discipline (no ground
truth in the model's input, every evidence claim must cite a real item,
a failed/ungrounded response falls back to a template).
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL = "claude-opus-5"

# Which evidence a reason code actually requires -- not every case needs
# every document type, matching PRD section 18's "evidence requirements
# depend on the reason code."
EVIDENCE_REQUIREMENTS = {
    "non_receipt": ["order_record", "payment_record", "delivery_confirmation"],
    "not_as_described": ["order_record", "payment_record", "delivery_confirmation", "product_listing"],
    "quality_issue": ["order_record", "payment_record", "delivery_confirmation", "product_listing"],
    "unauthorized": ["payment_record", "customer_history", "device_consistency"],
    "duplicate_charge": ["payment_record", "duplicate_check"],
}

SYSTEM_PROMPT = """You are drafting a chargeback dispute response for a payments risk team.

You are given a STRUCTURED CASE FILE: a dispute's evidence checklist, any contradictions already detected, and a recommendation (CONTEST / ACCEPT / ESCALATE) that a deterministic system already decided. Your job is to write the response text, not to decide the case.

STRICT RULES, no exceptions:
1. Only reference evidence items that appear in the input with status "present". Never claim a document exists if its status is "missing".
2. If any contradiction is listed, your response text must acknowledge it -- do not write a confident CONTEST narrative that ignores a listed contradiction.
3. Do not change the recommendation. If the input says ACCEPT or ESCALATE, do not draft text arguing to CONTEST.
4. Keep the response text professional, factual, and short (this goes to a card network or the merchant's own case file, not a customer).
5. If evidence is thin, say so plainly in the response rather than padding it with confident-sounding language.
"""


class ChargebackDraft(BaseModel):
    case_summary: str = Field(description="1-2 sentence summary of the dispute")
    response_text: str = Field(description="The actual text to submit (if CONTEST) or the internal case note (if ACCEPT/ESCALATE)")
    evidence_notes: list[str] = Field(description="Which evidence items support the response, referencing their exact names")
    caveats: list[str] = Field(default_factory=list, description="Anything a reviewer should double-check before submitting")


def _fallback_draft(case: dict) -> dict:
    present = [e["type"] for e in case["evidence"] if e["status"] == "present"]
    missing = [e["type"] for e in case["evidence"] if e["status"] != "present"]
    lines = [f"Case {case['case_id']}: {case['reason_code']} dispute, recommendation {case['recommendation']}."]
    if case["recommendation"] == "CONTEST":
        lines.append(f"Evidence on file: {', '.join(present) or 'none'}.")
    if case["contradictions"]:
        lines.append("Contradictions: " + "; ".join(c["description"] for c in case["contradictions"]))
    return {
        "case_summary": lines[0],
        "response_text": " ".join(lines),
        "evidence_notes": [f"{e} (present)" for e in present],
        "caveats": (["This is a template response (LLM investigator unavailable) -- restates the evidence "
                     "checklist rather than drafting submission-ready prose."]
                    + ([f"Missing evidence: {', '.join(missing)}"] if missing else [])),
        "_source": "deterministic_fallback",
    }


def _llm_input(case: dict) -> dict:
    """Everything the LLM may see -- no ground truth, ever."""
    return {
        "reason_code": case["reason_code"],
        "recommendation": case["recommendation"],
        "recommendation_reasoning": case["recommendation_reasoning"],
        "evidence_completeness": case["evidence_completeness"],
        "evidence": case["evidence"],
        "contradictions": case["contradictions"],
        "customer_prior_successful_deliveries": case["customer_context"]["prior_successful_deliveries"],
        "customer_is_established": case["customer_context"]["is_established"],
    }


def draft_response(client, case: dict) -> dict:
    try:
        response = client.messages.parse(
            model=MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Draft the response for this case:\n\n{json.dumps(_llm_input(case), indent=2, default=str)}"}],
            output_format=ChargebackDraft,
        )
        draft = response.parsed_output
        if draft is None:
            raise ValueError("no parsed output")
        result = draft.model_dump()
        result["_source"] = "llm"
        return result
    except Exception as e:  # noqa: BLE001
        result = _fallback_draft(case)
        result["_fallback_reason"] = f"{type(e).__name__}: {e}"
        return result


def _build_evidence(row, dispute_reason: str, prior_txns: pd.DataFrame, home_device_id, home_address_id) -> list:
    required = EVIDENCE_REQUIREMENTS.get(dispute_reason, ["order_record", "payment_record"])
    evidence = []

    def add(etype, present, detail):
        if etype in required:
            evidence.append({"type": etype, "status": "present" if present else "missing", "detail": detail})

    add("order_record", True, f"Order {row.transaction_id} for {row.product_id}, placed {row.timestamp}")
    add("payment_record", True, f"{row.payment_method} payment of Rs {row.amount:,.2f}")
    add("product_listing", True, f"Product {row.product_id}")
    add("delivery_confirmation", row.status == "approved", (
        "Order was authorized and processed" if row.status == "approved" else "Order was not successfully authorized"
    ))
    add("customer_history", len(prior_txns) > 0, f"{len(prior_txns)} prior transactions on file")
    add("device_consistency", row.device_id == home_device_id, (
        "Transaction device matches customer's usual device" if row.device_id == home_device_id
        else "Transaction device differs from customer's usual device"
    ))

    if dispute_reason == "duplicate_charge":
        window = prior_txns[
            (prior_txns["amount"] == row.amount)
            & (abs((pd.to_datetime(prior_txns["timestamp"]) - pd.to_datetime(row.timestamp)).dt.total_seconds()) < 48 * 3600)
        ]
        add("duplicate_check", len(window) == 0, (
            "No other transaction of the same amount within 48 hours" if len(window) == 0
            else f"{len(window)} other transaction(s) of the same amount within 48 hours -- possible genuine duplicate"
        ))

    return evidence


def build_cases(transactions: pd.DataFrame, customers: pd.DataFrame, loss_events: list, fused_scores: dict,
                 scope_split: Optional[str] = None) -> list:
    customers_idx = customers.set_index("customer_id")
    txn_id_to_event = {}
    for event in loss_events:
        for tid in event["transaction_ids"]:
            # keep the highest-confidence event if a transaction somehow appears in more than one
            if tid not in txn_id_to_event or event["confidence"] > txn_id_to_event[tid]["confidence"]:
                txn_id_to_event[tid] = event

    disputed = transactions[transactions["is_disputed"]]
    if scope_split is not None:
        # Only the CASES are scoped -- prior-history lookups below still use
        # the full `transactions` frame, so a test-split dispute still sees
        # a customer's real train/val history instead of undercounting it.
        disputed = disputed[disputed["split"] == scope_split]
    disputed = disputed.sort_values("timestamp")
    cases = []
    for i, row in enumerate(disputed.itertuples(index=False), start=1):
        cust = customers_idx.loc[row.customer_id] if row.customer_id in customers_idx.index else None
        prior_txns = transactions[
            (transactions["customer_id"] == row.customer_id) & (transactions["timestamp"] < row.timestamp)
        ]
        prior_successful = prior_txns[
            (prior_txns["status"] == "approved") & (~prior_txns["is_returned"]) & (~prior_txns["is_disputed"])
        ]

        evidence = _build_evidence(
            row, row.dispute_reason, prior_txns,
            cust["home_device_id"] if cust is not None else None,
            cust["home_address_id"] if cust is not None else None,
        )
        required = EVIDENCE_REQUIREMENTS.get(row.dispute_reason, [])
        completeness = round(sum(e["status"] == "present" for e in evidence) / max(len(required), 1), 3)

        linked_event = txn_id_to_event.get(row.transaction_id)
        txn_fused_score = fused_scores.get(row.transaction_id, 0.0)
        # The strongest independent risk signal for this transaction, whichever
        # source produced it: a formal cluster/temporal event, or (when the
        # transaction wasn't swept into one -- graph/anomaly detection isn't
        # 100% recall, see docs/EVALUATION.md) its own fused score from the
        # same engines. Using only event membership here misses real fraud
        # that individual detection still caught; verified empirically this
        # closes most of the gap (see ml/README.md).
        independent_risk_score = max(linked_event["confidence"] if linked_event else 0.0, txn_fused_score)

        contradictions = []
        if row.is_refunded:
            contradictions.append({
                "type": "refund_already_issued",
                "description": (
                    f"A refund was already issued for this order (on {row.refunded_at}), which may undercut "
                    f"a '{row.dispute_reason}' dispute -- the merchant's own records show the issue was "
                    f"already addressed before the dispute arrived."
                ),
            })
        if linked_event and linked_event["confidence"] >= 0.7:
            contradictions.append({
                "type": "independently_flagged_as_loss",
                "description": (
                    f"This transaction is part of Loss Event {linked_event['event_id']} "
                    f"({linked_event['event_type']}), independently flagged by this system's own risk engine "
                    f"at {linked_event['confidence']:.0%} confidence."
                ),
            })
        elif txn_fused_score >= 0.6:
            contradictions.append({
                "type": "independently_flagged_as_risky",
                "description": (
                    f"This transaction's own fused risk score ({txn_fused_score:.0%}) was elevated "
                    f"independently of this dispute, though it wasn't part of a formal Loss Event."
                ),
            })

        if independent_risk_score >= 0.6:
            reason = (f"Loss Event {linked_event['event_id']} ({linked_event['event_type']})"
                      if linked_event and linked_event["confidence"] >= 0.6
                      else f"its own fused risk score ({txn_fused_score:.0%})")
            recommendation = "ACCEPT"
            reasoning = (
                f"Transaction was independently flagged as high-risk via {reason}, detected before this "
                f"dispute arrived. Contesting would contradict this system's own fraud finding."
            )
        elif any(c["type"] == "refund_already_issued" for c in contradictions):
            recommendation = "ESCALATE"
            reasoning = "A refund was already issued for this order -- needs manual review before responding."
        elif completeness >= 0.66:
            recommendation = "CONTEST"
            reasoning = f"{completeness:.0%} of the evidence this reason code requires is on file, with no contradictions."
        elif completeness >= 0.33:
            recommendation = "ESCALATE"
            reasoning = f"Only {completeness:.0%} of required evidence is on file -- not enough to confidently contest."
        else:
            recommendation = "ACCEPT"
            reasoning = f"Only {completeness:.0%} of required evidence is on file -- contesting is unlikely to succeed."

        case = {
            "case_id": f"CB-{i:04d}",
            "transaction_id": row.transaction_id,
            "merchant_id": row.merchant_id,
            "customer_id": row.customer_id,
            "amount": row.amount,
            "reason_code": row.dispute_reason,
            "disputed_at": str(row.disputed_at),
            "order_timestamp": str(row.timestamp),
            "evidence": evidence,
            "evidence_completeness": completeness,
            "contradictions": contradictions,
            "recommendation": recommendation,
            "recommendation_reasoning": reasoning,
            "linked_loss_event": {
                "event_id": linked_event["event_id"], "event_type": linked_event["event_type"],
                "confidence": linked_event["confidence"],
            } if linked_event else None,
            "transaction_fused_score": round(float(txn_fused_score), 4),
            "customer_context": {
                "prior_transaction_count": int(len(prior_txns)),
                "prior_successful_deliveries": int(len(prior_successful)),
                "is_established": len(prior_txns) > 0,
            },
        }
        cases.append(case)

    return cases


def _ground_truth_summary(case: dict, labels_by_txn: dict) -> dict:
    label = labels_by_txn.get(case["transaction_id"], {})
    return {
        "is_true_loss": label.get("category") == "loss",
        "true_scenario_type": label.get("scenario_type"),
    }


def run(out_path: Path) -> list:
    transactions = pd.read_csv(DATA_DIR / "transactions.csv", parse_dates=["timestamp", "disputed_at", "refunded_at"])
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    with open(ARTIFACT_DIR / "loss_events_with_policy.json") as f:
        loss_events = json.load(f)
    fused = pd.read_csv(ARTIFACT_DIR / "fused_scores.csv")
    fused_scores = dict(zip(fused["transaction_id"], fused["fused_score"]))

    # Cases are scoped to the test split, same as every other held-out
    # number in this repo: loss_events_with_policy.json (and therefore the
    # loss-event link) and fused_scores.csv only exist for test-split
    # transactions, so a train/val dispute would never find a match --
    # scoping here keeps the comparison honest instead of silently
    # degrading on 2/3 of the data. Prior-history lookups still see the
    # customer's full train/val/test record (see build_cases).
    cases = build_cases(transactions, customers, loss_events, fused_scores, scope_split="test")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = None
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

    llm_count, fallback_count = 0, 0
    for case in cases:
        case["draft"] = draft_response(client, case) if client is not None else _fallback_draft(case)
        if case["draft"]["_source"] == "llm":
            llm_count += 1
        else:
            fallback_count += 1

    with open(out_path, "w") as f:
        json.dump(cases, f, indent=2, default=str)

    print(f"  {len(cases)} chargeback cases built, {llm_count} drafted by {MODEL}, {fallback_count} by deterministic fallback")
    return cases


if __name__ == "__main__":
    print("Building chargeback cases...")
    cases = run(ARTIFACT_DIR / "chargeback_cases.json")

    print("\n=== Recommendation distribution ===")
    df = pd.DataFrame([{
        "case_id": c["case_id"], "reason_code": c["reason_code"], "recommendation": c["recommendation"],
        "evidence_completeness": c["evidence_completeness"], "linked_event": bool(c["linked_loss_event"]),
        "n_contradictions": len(c["contradictions"]),
    } for c in cases])
    print(df["recommendation"].value_counts())
    print("\n=== Cases with contradictions ===")
    print(df[df["n_contradictions"] > 0][["case_id", "reason_code", "recommendation", "n_contradictions"]])

    # Evaluation-only cross-check against ground truth -- never used to build the cases above.
    labels = pd.read_csv(DATA_DIR / "ground_truth" / "transaction_labels.csv").set_index("transaction_id")
    labels_by_txn = labels.to_dict(orient="index")
    for c in cases:
        c["_ground_truth"] = _ground_truth_summary(c, labels_by_txn)

    gt_df = pd.DataFrame([{
        "recommendation": c["recommendation"], "is_true_loss": c["_ground_truth"]["is_true_loss"],
    } for c in cases])
    print("\n=== Evaluation-only: recommendation vs ground truth ===")
    print(pd.crosstab(gt_df["recommendation"], gt_df["is_true_loss"]))

    with open(ARTIFACT_DIR / "chargeback_cases.json", "w") as f:
        json.dump(cases, f, indent=2, default=str)
