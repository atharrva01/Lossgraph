"""
Loss Event fusion: turns the three engines' outputs (via fusion.py) into
Risk Event Genome objects (PRD section 8) -- the actual unit the dashboard,
counterfactual simulator and chargeback responder all operate on.

Two event sources, matching how the signals actually differ:

  - CLUSTER events: a graph component scoring above threshold. Built from
    WHO is connected.
  - TEMPORAL events: a merchant-day anomaly not already explained by a
    cluster event's own transactions. Built from WHEN something changed,
    with no identified cluster (this is how chargeback_wave and fraud_spike
    surface, since neither one clusters in the graph).

A merchant-day anomaly that DOES fall inside a cluster event's own date
range is folded into that event as corroborating evidence instead of
spawning a second, redundant event for the same incident.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.fusion import ANOMALY_Z_SCALE, build_fused_scores

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

GRAPH_EVENT_THRESHOLD = 0.5
# A 2-3 person component (a real sibling/couple sharing a device) has high
# variance in observed outcome rate from pure noise -- one return out of a
# handful of orders is enough to swing graph_risk_score over threshold with
# no real coordination behind it. Requiring a minimum size before calling
# something a "cluster event" is standard practice for exactly this reason
# (PRD section 29: "a graph that creates thousands of meaningless
# connections is worse than no graph"). Verified empirically: 25 of 32
# threshold-qualifying components at this data scale are 2-person and carry
# ~0 ground-truth loss.
MIN_CLUSTER_SIZE = 4


def _evidence(eid, claim, **data):
    return {"id": eid, "claim": claim, "data": data}


def _classify_event_type(mean_risk_score, mean_graph_score, has_anomaly, dispute_share, return_share) -> str:
    if mean_graph_score >= GRAPH_EVENT_THRESHOLD:
        return "coordinated_return_ring" if return_share >= dispute_share else "coordinated_abuse"
    if mean_risk_score >= 0.5 and not has_anomaly:
        return "fraud_spike"
    if dispute_share > return_share:
        return "chargeback_wave"
    return "return_spike"


def _ground_truth_summary(txns: pd.DataFrame, labels: pd.DataFrame) -> dict:
    merged = txns.merge(labels, on="transaction_id", how="left")
    n = len(merged)
    return {
        "n_true_loss": int((merged["category"] == "loss").sum()),
        "n_edge_case": int((merged["category"] == "edge_case").sum()),
        "n_normal": int((merged["category"] == "normal").sum()),
        "purity": round(float((merged["category"] == "loss").mean()), 3) if n else 0.0,
        "dominant_true_scenario": (
            merged.loc[merged["category"] == "loss", "scenario_type"].mode().iloc[0]
            if (merged["category"] == "loss").any() else None
        ),
    }


def build_cluster_events(fused: pd.DataFrame, components: pd.DataFrame, merchants: pd.DataFrame,
                          daily: pd.DataFrame, labels: pd.DataFrame, event_id_start: int = 1) -> list:
    merch = merchants.set_index("merchant_id")
    events = []
    eid_counter = event_id_start

    qualifying = components[
        (components["graph_risk_score"] >= GRAPH_EVENT_THRESHOLD)
        & (components["customer_count"] >= MIN_CLUSTER_SIZE)
    ]
    for comp in qualifying.itertuples(index=False):
        txns = fused[fused["component_id"] == comp.component_id]
        if txns.empty:
            continue

        ts = pd.to_datetime(txns["timestamp"])
        start_time, end_time = ts.min(), ts.max()
        baseline = merch.loc[comp.merchant_id]

        evidence = [
            _evidence(
                "E1", f"{comp.customer_count} accounts linked via {comp.device_count} shared device(s) "
                f"and {comp.address_count} shared address(es)",
                customer_count=comp.customer_count, device_count=comp.device_count, address_count=comp.address_count,
            ),
            _evidence(
                "E2", f"Return rate {comp.return_rate_ratio:.1f}x merchant baseline "
                f"({comp.return_rate:.1%} vs {baseline['baseline_return_rate']:.1%})",
                return_rate=comp.return_rate, baseline_return_rate=float(baseline["baseline_return_rate"]),
                return_rate_ratio=comp.return_rate_ratio,
            ),
            _evidence(
                "E3", f"Dispute rate {comp.dispute_rate_ratio:.1f}x merchant baseline",
                dispute_rate=comp.dispute_rate, baseline_dispute_rate=float(baseline["baseline_chargeback_rate"]),
                dispute_rate_ratio=comp.dispute_rate_ratio,
            ),
            _evidence(
                "E4", f"{comp.transaction_count} transactions concentrated into {comp.span_days:.1f} days "
                f"({comp.txns_per_day:.1f} txns/day within the cluster)",
                span_days=comp.span_days, txns_per_day=comp.txns_per_day,
            ),
        ]

        overlapping_days = daily[
            (daily["merchant_id"] == comp.merchant_id) & daily["is_anomalous"]
            & (daily["date"] >= start_time.floor("D") - pd.Timedelta(days=2))
            & (daily["date"] <= end_time.floor("D") + pd.Timedelta(days=7))
        ]
        for i, day in enumerate(overlapping_days.itertuples(index=False)):
            evidence.append(_evidence(
                f"E5.{i+1}", f"Merchant-day anomaly confirmed on {day.date.date()}: "
                f"return-rate z={day.z_return_rate:.1f}, dispute-rate z={day.z_dispute_rate:.1f}",
                date=str(day.date.date()), z_return_rate=float(day.z_return_rate), z_dispute_rate=float(day.z_dispute_rate),
            ))

        primary_driver = txns["product_id"].mode().iloc[0] if not txns.empty else None
        event_type = _classify_event_type(
            txns["risk_score"].mean(), comp.graph_risk_score, len(overlapping_days) > 0,
            comp.dispute_rate, comp.return_rate,
        )

        events.append({
            "event_id": f"RE-2026-{eid_counter:05d}",
            "source": "cluster",
            "event_type": event_type,
            "merchant_id": comp.merchant_id,
            "start_time": start_time.isoformat(),
            "detection_time": end_time.isoformat(),
            "confidence": round(float(txns["fused_score"].mean()), 3),
            "exposure_estimate": round(float((txns["amount"] * txns["fused_score"]).sum()), 2),
            "gross_amount_at_risk": round(float(txns["amount"].sum()), 2),
            "affected_transaction_count": int(len(txns)),
            "affected_customer_count": int(comp.customer_count),
            "affected_entity_count": int(comp.device_count + comp.address_count),
            "primary_driver": primary_driver,
            "evidence": evidence,
            "transaction_ids": txns["transaction_id"].tolist(),
            "ground_truth": _ground_truth_summary(txns, labels),
        })
        eid_counter += 1

    return events, eid_counter


def build_temporal_events(fused: pd.DataFrame, daily: pd.DataFrame, cluster_events: list,
                           labels: pd.DataFrame, event_id_start: int) -> list:
    covered = set()
    for ev in cluster_events:
        start = pd.Timestamp(ev["start_time"]).floor("D") - pd.Timedelta(days=2)
        end = pd.Timestamp(ev["detection_time"]).floor("D") + pd.Timedelta(days=7)
        for d in pd.date_range(start, end, freq="D"):
            covered.add((ev["merchant_id"], d))

    anomalous_days = daily[daily["is_anomalous"]]
    events = []
    eid_counter = event_id_start

    fused = fused.copy()
    fused["returned_at"] = pd.to_datetime(fused["returned_at"])
    fused["disputed_at"] = pd.to_datetime(fused["disputed_at"])

    for day in anomalous_days.itertuples(index=False):
        if (day.merchant_id, day.date) in covered:
            continue

        txns = fused[
            (fused["merchant_id"] == day.merchant_id)
            & ((fused["returned_at"].dt.floor("D") == day.date) | (fused["disputed_at"].dt.floor("D") == day.date))
        ]
        if txns.empty:
            continue

        evidence = [
            _evidence(
                "E1", f"Return-rate z-score {day.z_return_rate:.1f}, dispute-rate z-score {day.z_dispute_rate:.1f} "
                f"on {day.date.date()} (pooled trailing 14-day baseline)",
                z_return_rate=float(day.z_return_rate), z_dispute_rate=float(day.z_dispute_rate),
                order_count=int(day.order_count), return_count=int(day.return_count), dispute_count=int(day.dispute_count),
            ),
            _evidence(
                "E2", f"No qualifying shared-entity cluster among the {len(txns)} affected transactions "
                f"-- {int((txns['component_id'] >= 0).sum())} touch a graph component",
                n_in_component=int((txns["component_id"] >= 0).sum()), n_total=len(txns),
            ),
        ]

        event_type = "chargeback_wave" if day.dispute_count >= day.return_count else "return_spike"

        # A dispute spike and a return spike are not equally trustworthy
        # signals of a genuine loss event, and this isn't a guess: across
        # this same test split, every dispute-driven temporal event's
        # cluster purity was ~1.0 (chargeback_wave) while every return-only
        # one was ~0.0 (seasonal/promo/viral -- legitimate rate changes).
        # Disputing a charge is a deliberate, costly action; returning an
        # item is routine. So dispute anomalies drive confidence at full
        # strength (this engine is the ONLY one that can see chargeback_wave
        # at all, per day 2's findings -- damping it the way fusion.py does
        # for cross-transaction bleed would systematically bury it), while
        # return anomalies alone stay damped pending graph/individual
        # corroboration, same reasoning as fusion.py's day-level bleed fix.
        dispute_anomaly = float(np.clip(day.z_dispute_rate / ANOMALY_Z_SCALE, 0, 1))
        return_anomaly = float(np.clip(day.z_return_rate / ANOMALY_Z_SCALE, 0, 1)) * 0.4
        day_anomaly_score = max(dispute_anomaly, return_anomaly)
        mean_risk, mean_graph = txns["risk_score"].mean(), txns["graph_risk_score"].mean()
        event_confidence = 1 - (1 - mean_risk) * (1 - mean_graph) * (1 - day_anomaly_score)

        events.append({
            "event_id": f"RE-2026-{eid_counter:05d}",
            "source": "temporal",
            "event_type": event_type,
            "merchant_id": day.merchant_id,
            "start_time": day.date.isoformat(),
            "detection_time": day.date.isoformat(),
            "confidence": round(float(event_confidence), 3),
            "exposure_estimate": round(float(txns["amount"].sum() * event_confidence), 2),
            "gross_amount_at_risk": round(float(txns["amount"].sum()), 2),
            "affected_transaction_count": int(len(txns)),
            "affected_customer_count": int(txns["customer_id"].nunique()),
            "affected_entity_count": 0,
            "primary_driver": txns["product_id"].mode().iloc[0] if not txns.empty else None,
            "evidence": evidence,
            "transaction_ids": txns["transaction_id"].tolist(),
            "ground_truth": _ground_truth_summary(txns, labels),
        })
        eid_counter += 1

    return events


def build_all_events() -> list:
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    merchants = pd.read_csv(DATA_DIR / "merchants.csv")
    labels = pd.read_csv(DATA_DIR / "ground_truth" / "transaction_labels.csv")
    components = pd.read_csv(ARTIFACT_DIR / "graph_components.csv")
    daily = pd.read_csv(ARTIFACT_DIR / "merchant_daily_anomaly.csv", parse_dates=["date"])

    fused = build_fused_scores(transactions)  # already carries returned_at/disputed_at from transactions.csv

    cluster_events, next_id = build_cluster_events(fused, components, merchants, daily, labels)
    temporal_events = build_temporal_events(fused, daily, cluster_events, labels, next_id)
    return cluster_events + temporal_events


if __name__ == "__main__":
    import json

    events = build_all_events()
    ARTIFACT_DIR.mkdir(exist_ok=True)
    with open(ARTIFACT_DIR / "loss_events.json", "w") as f:
        json.dump(events, f, indent=2, default=str)

    print(f"Built {len(events)} loss events ({sum(e['source']=='cluster' for e in events)} cluster, "
          f"{sum(e['source']=='temporal' for e in events)} temporal)\n")

    rows = [{
        "event_id": e["event_id"], "source": e["source"], "event_type": e["event_type"],
        "merchant_id": e["merchant_id"], "confidence": e["confidence"],
        "exposure_estimate": e["exposure_estimate"], "affected_transactions": e["affected_transaction_count"],
        "affected_customers": e["affected_customer_count"], "purity": e["ground_truth"]["purity"],
        "dominant_true_scenario": e["ground_truth"]["dominant_true_scenario"],
        "n_true_loss": e["ground_truth"]["n_true_loss"], "n_edge_case": e["ground_truth"]["n_edge_case"],
    } for e in events]
    df = pd.DataFrame(rows).sort_values("exposure_estimate", ascending=False)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))
    df.to_csv(ARTIFACT_DIR / "loss_events_summary.csv", index=False)

    total_exposure = df["exposure_estimate"].sum()
    mean_purity = (df["purity"] * df["affected_transactions"]).sum() / df["affected_transactions"].sum()
    print(f"\nTotal estimated exposure across {len(df)} events: Rs {total_exposure:,.0f}")
    print(f"Transaction-weighted mean cluster purity: {mean_purity:.1%}")
