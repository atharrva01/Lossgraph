"""
AI Investigation Layer (PRD section 16-17, 37).

Turns a Loss Event's already-computed evidence chain into a plain-English
investigation narrative for a human analyst. The LLM investigates
structured evidence; it does not decide fraud, does not modify any score,
and cannot recommend an action other than the one the deterministic
counterfactual simulator already chose. Every claim in the narrative must
cite an evidence ID (E1, E2, ...) from the input -- enforced by instruction,
not just requested, and checked post-hoc (see `_citations_present`).

Ground truth is deliberately never included in the LLM's input. A real
deployment doesn't have it; leaking it here would let the model parrot the
answer instead of reasoning from evidence, which would defeat the entire
point of testing whether the narrative stays grounded.

Failure handling (PRD section 43): if the API is unreachable, unconfigured,
or returns something that fails validation, this falls back to a
deterministic template built from the same evidence -- the pipeline never
depends on the LLM being available, and the fallback is not a lesser
citizen: it's evidence-complete, just not prose-varied.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are a fraud/risk investigation assistant writing up a case file for a human analyst at a payments company.

You are given STRUCTURED EVIDENCE about a "Loss Event" that deterministic statistical and graph algorithms already detected and scored. Your job is to explain it in plain English -- you do not detect anything yourself.

STRICT RULES, no exceptions:
1. Every sentence in `supporting_evidence` and `contradicting_evidence` MUST end with the evidence ID(s) it is drawn from in parentheses, e.g. "(E1)" or "(E2, E4)". If a claim has no matching evidence ID, do not make the claim.
2. Do not invent any fact, number, entity, or evidence not present in the input. If you want to say something the evidence doesn't establish, put it in `unknowns` instead, phrased as a question or gap -- not as a claim.
3. Do not independently decide whether this is fraud. Report what the evidence shows and how confident the system already is (the `confidence` field) -- do not assign your own confidence.
4. The `recommended_next_step` must describe and justify the action already given to you in the input's `recommended_action` field. Do not propose a different action. If the evidence seems weak for that action, say so honestly in `unknowns`, not by silently recommending something else.
5. If the evidence is sparse, mixed, or low-confidence, say that plainly. A short, honest write-up beats a padded confident-sounding one.
"""


class InvestigationNarrative(BaseModel):
    incident_summary: str = Field(description="2-3 sentence plain-English summary of what was detected")
    primary_hypothesis: str = Field(description="The most likely explanation, grounded in the evidence")
    supporting_evidence: list[str] = Field(description="Each item must cite evidence ID(s) in parentheses")
    contradicting_evidence: list[str] = Field(
        default_factory=list, description="Evidence that cuts against the primary hypothesis, if any -- empty list if none"
    )
    unknowns: list[str] = Field(
        default_factory=list, description="What the evidence does not establish -- gaps, not guesses"
    )
    recommended_next_step: str = Field(description="Explains the already-computed recommended_action, does not invent a new one")
    confidence_commentary: str = Field(description="Plain-English explanation of what the numeric confidence means here")


def _build_input_payload(event: dict) -> dict:
    """Everything the LLM is allowed to see. No ground_truth, ever."""
    return {
        "event_type": event["event_type"],
        "source": event["source"],
        "merchant_id": event["merchant_id"],
        "confidence": event["confidence"],
        "exposure_estimate": event["exposure_estimate"],
        "affected_transaction_count": event["affected_transaction_count"],
        "affected_customer_count": event["affected_customer_count"],
        "primary_driver": event["primary_driver"],
        "evidence": event["evidence"],
        "recommended_action": event["counterfactual"]["recommended_action"],
        "policy_comparison_summary": [
            {"action": s["action"], "net_benefit": s["net_benefit"]}
            for s in event["counterfactual"]["simulations"]
        ],
    }


def _citations_present(narrative: InvestigationNarrative, valid_ids: set[str]) -> bool:
    """Post-hoc grounding check: every supporting/contradicting claim must
    cite at least one real evidence ID. Not a guarantee the citation is used
    correctly, but catches the model dropping citations entirely."""
    for claim in narrative.supporting_evidence + narrative.contradicting_evidence:
        if not any(eid in claim for eid in valid_ids):
            return False
    return True


def _fallback_narrative(event: dict) -> dict:
    """Deterministic, evidence-complete narrative built with zero LLM calls."""
    ev = event["evidence"]
    cf = event["counterfactual"]
    supporting = [f"{e['claim']} ({e['id']})" for e in ev]
    return {
        "incident_summary": (
            f"{event['event_type'].replace('_', ' ').title()} detected at merchant {event['merchant_id']}, "
            f"affecting {event['affected_transaction_count']} transactions across "
            f"{event['affected_customer_count']} customers. Estimated exposure "
            f"Rs {event['exposure_estimate']:,.0f} at {event['confidence']:.0%} confidence."
        ),
        "primary_hypothesis": f"See evidence chain ({', '.join(e['id'] for e in ev)}).",
        "supporting_evidence": supporting,
        "contradicting_evidence": [],
        "unknowns": [
            "This is a template summary (LLM investigator unavailable) -- it restates the evidence chain "
            "verbatim rather than synthesizing a hypothesis. See the Evidence panel for the same data."
        ],
        "recommended_next_step": (
            f"System recommends: {cf['recommended_action'].upper()}. See the policy comparison table for "
            f"the economic reasoning."
        ),
        "confidence_commentary": f"Fused confidence score: {event['confidence']:.0%}.",
        "_source": "deterministic_fallback",
    }


def investigate_event(client, event: dict) -> dict:
    payload = _build_input_payload(event)
    valid_ids = {e["id"] for e in event["evidence"]}

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Investigate this Loss Event:\n\n{json.dumps(payload, indent=2, default=str)}",
            }],
            output_format=InvestigationNarrative,
        )
        narrative = response.parsed_output
        if narrative is None or not _citations_present(narrative, valid_ids):
            raise ValueError("model output failed grounding check (missing evidence citations)")
        result = narrative.model_dump()
        result["_source"] = "llm"
        return result
    except Exception as e:  # noqa: BLE001 -- any failure falls back, never blocks the pipeline
        result = _fallback_narrative(event)
        result["_fallback_reason"] = f"{type(e).__name__}: {e}"
        return result


def run(events_path: Path) -> list:
    with open(events_path) as f:
        events = json.load(f)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = None
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            print("  anthropic package not installed -- falling back to deterministic narratives for all events")
    else:
        print("  ANTHROPIC_API_KEY not set -- falling back to deterministic narratives for all events "
              "(this is the section-43 'LLM unavailable' failure path, not an error)")

    llm_count, fallback_count = 0, 0
    for event in events:
        if client is not None:
            event["investigation"] = investigate_event(client, event)
        else:
            event["investigation"] = _fallback_narrative(event)
        if event["investigation"]["_source"] == "llm":
            llm_count += 1
        else:
            fallback_count += 1

    with open(events_path, "w") as f:
        json.dump(events, f, indent=2, default=str)

    print(f"  {llm_count} narratives generated by {MODEL}, {fallback_count} by deterministic fallback")
    return events


if __name__ == "__main__":
    events_path = ARTIFACT_DIR / "loss_events_with_policy.json"
    print(f"Investigating {json.load(open(events_path)).__len__()} events...")
    run(events_path)
