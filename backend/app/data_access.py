"""
Loads the pipeline's precomputed outputs (data/output/ + ml/artifacts/) and
serves them to the API layer.

Deliberately NOT the SQLAlchemy/DB path the original scaffold sketched:
the intelligence pipeline (data/generation/ + ml/) is an offline batch
process -- exactly like a real risk system's nightly/streaming scoring job
-- and the API's job is to serve its output, not recompute it per request.
Everything here is loaded once and cached in memory; at this data scale
(tens of thousands of rows) that's simpler and faster than a DB round trip,
and it keeps "regenerate the demo dataset" and "serve the demo dataset" as
clearly separate steps, which is how this would actually be deployed.
"""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "output"
ARTIFACT_DIR = ROOT / "ml" / "artifacts"


class PipelineNotRunError(RuntimeError):
    pass


def _require(path: Path):
    if not path.exists():
        raise PipelineNotRunError(
            f"Missing {path.relative_to(ROOT)}. Run `make pipeline` (data generation + ml engines) first."
        )
    return path


@lru_cache(maxsize=1)
def load_events() -> list:
    with open(_require(ARTIFACT_DIR / "loss_events_with_policy.json")) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_merchants() -> pd.DataFrame:
    return pd.read_csv(_require(DATA_DIR / "merchants.csv"))


@lru_cache(maxsize=1)
def load_entities() -> pd.DataFrame:
    return pd.read_csv(_require(DATA_DIR / "entities.csv"))


@lru_cache(maxsize=1)
def load_relationships() -> pd.DataFrame:
    return pd.read_csv(_require(DATA_DIR / "relationships.csv"))


@lru_cache(maxsize=1)
def load_transactions() -> pd.DataFrame:
    return pd.read_csv(_require(DATA_DIR / "transactions.csv"), parse_dates=["timestamp"])


@lru_cache(maxsize=1)
def load_customers() -> pd.DataFrame:
    return pd.read_csv(_require(DATA_DIR / "customers.csv"))


@lru_cache(maxsize=1)
def load_chargeback_cases() -> list:
    with open(_require(ARTIFACT_DIR / "chargeback_cases.json")) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_fused_scores() -> pd.DataFrame:
    return pd.read_csv(_require(ARTIFACT_DIR / "fused_scores.csv"))


def get_event(event_id: str) -> dict | None:
    return next((e for e in load_events() if e["event_id"] == event_id), None)


def get_chargeback_case(case_id: str) -> dict | None:
    return next((c for c in load_chargeback_cases() if c["case_id"] == case_id), None)


def chargeback_cases_for_event(event_id: str) -> list:
    return [c for c in load_chargeback_cases() if c.get("linked_loss_event") and c["linked_loss_event"]["event_id"] == event_id]


def merchant_name(merchant_id: str) -> str:
    merchants = load_merchants().set_index("merchant_id")
    return merchants.loc[merchant_id, "name"] if merchant_id in merchants.index else merchant_id


def command_center_summary(merchant_id: str | None = None) -> dict:
    events = load_events()
    if merchant_id and merchant_id != "ALL":
        events = [e for e in events if e["merchant_id"] == merchant_id]

    total_exposure = sum(e["exposure_estimate"] for e in events)
    active_events = [e for e in events if e["counterfactual"]["recommended_action"] != "allow"]
    preventable_exposure = sum(
        next(s for s in e["counterfactual"]["simulations"] if s["action"] == e["counterfactual"]["recommended_action"])
        ["expected_loss_prevented"]
        for e in active_events
    )
    net_benefit = sum(
        next(s for s in e["counterfactual"]["simulations"] if s["action"] == e["counterfactual"]["recommended_action"])
        ["net_benefit"]
        for e in events
    )

    return {
        "merchant_id": merchant_id or "ALL",
        "current_exposure": round(total_exposure, 2),
        "preventable_exposure": round(preventable_exposure, 2),
        "active_incidents": len(active_events),
        "total_incidents": len(events),
        "net_benefit_vs_allow": round(net_benefit, 2),
    }


def engine_breakdown_for_event(event: dict) -> dict:
    """The three per-engine scores that produced this event's confidence.

    Read from confidence_components, computed by ml/loss_events.py at the
    same time as confidence itself -- for a temporal event that's the
    merchant-day anomaly z-score, NOT a mean of the per-transaction
    anomaly_score column (those are different numbers; averaging the wrong
    one previously produced a breakdown that silently contradicted the
    headline confidence). Falling back to a live re-derivation from
    fused_scores.csv only covers an artifact built before this field
    existed, and is only exact for cluster-source events.
    """
    components = event.get("confidence_components")
    if components:
        return {**components, "fused": event["confidence"]}

    fused = load_fused_scores()
    txns = fused[fused["transaction_id"].isin(event["transaction_ids"])]
    if txns.empty:
        return {"transaction_model": 0.0, "graph_engine": 0.0, "temporal_anomaly": 0.0, "fused": event["confidence"]}
    return {
        "transaction_model": round(float(txns["risk_score"].mean()), 4),
        "graph_engine": round(float(txns["graph_risk_score"].mean()), 4),
        "temporal_anomaly": round(float(txns["anomaly_score"].mean()), 4),
        "fused": round(float(txns["fused_score"].mean()), 4),
    }


def graph_for_event(event: dict) -> dict:
    """Cytoscape-ready {nodes, edges} for a cluster event's affected
    customers plus the devices/addresses connecting them. Temporal events
    (no qualifying cluster) return an empty graph -- that absence is itself
    the point (evidence E2 already says so)."""
    if event["source"] != "cluster":
        return {"nodes": [], "edges": []}

    transactions = load_transactions()
    txns = transactions[transactions["transaction_id"].isin(event["transaction_ids"])]
    customer_ids = set(txns["customer_id"])

    relationships = load_relationships()
    rel = relationships[
        relationships["source_entity_id"].isin(customer_ids)
        & relationships["relationship_type"].isin(["USED_DEVICE", "USED_ADDRESS"])
    ]

    entity_ids = set(rel["target_entity_id"]) | customer_ids
    entities = load_entities().set_index("entity_id")
    customers = load_customers().set_index("customer_id")

    nodes = []
    for eid in entity_ids:
        if eid in customers.index:
            cust = customers.loc[eid]
            nodes.append({
                "id": eid, "type": "customer",
                "label": eid,
                "segment": cust.get("true_archetype", "unknown"),
            })
        elif eid in entities.index:
            etype = entities.loc[eid, "entity_type"]
            nodes.append({"id": eid, "type": etype, "label": eid})

    edges = [
        {
            "id": r.relationship_id, "source": r.source_entity_id, "target": r.target_entity_id,
            "type": r.relationship_type, "frequency": int(r.frequency), "confidence": float(r.confidence),
        }
        for r in rel.itertuples(index=False)
    ]
    return {"nodes": nodes, "edges": edges}
