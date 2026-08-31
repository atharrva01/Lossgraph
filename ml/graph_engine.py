"""
Engine 3 -- Entity Graph Engine.

Builds a bipartite customer<->device/address graph (product co-purchase is
deliberately excluded -- too promiscuous a signal, it would merge unrelated
customers through nothing stronger than "bought the same popular SKU").
Connected components are the graph's native notion of a cluster; each
component gets a heuristic risk score from three ingredients:

  - outcome concentration: the component's realized return/dispute rate
    relative to its merchant's baseline
  - burstiness: transactions/day within the component (a ring is compressed
    into hours; legitimate sharing -- household, corporate -- is steady)
  - size: log-scaled customer count in the component

This is deliberately NOT a trained model (PRD section 14: start with graph
algorithms, not a GNN). Unlike the transaction risk model, this engine is a
retrospective investigation tool, not a real-time authorization score --
it's allowed to use realized outcomes (returns/disputes that have already
happened), the same way a fraud analyst reviewing a graph would.
"""

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"
IDENTITY_RELATIONSHIP_TYPES = {"USED_DEVICE", "USED_ADDRESS"}


def build_graph(entities: pd.DataFrame, relationships: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for row in entities.itertuples(index=False):
        G.add_node(row.entity_id, entity_type=row.entity_type)
    identity_rels = relationships[relationships["relationship_type"].isin(IDENTITY_RELATIONSHIP_TYPES)]
    for row in identity_rels.itertuples(index=False):
        G.add_edge(
            row.source_entity_id, row.target_entity_id,
            relationship_type=row.relationship_type, confidence=row.confidence, frequency=row.frequency,
        )
    return G


def score_components(G: nx.Graph, transactions: pd.DataFrame, merchants: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per qualifying component (>=2 customers) with a graph_risk_score."""
    merch = merchants.set_index("merchant_id")
    txn_by_customer = transactions.groupby("customer_id")

    rows = []
    for comp_id, component in enumerate(nx.connected_components(G)):
        customer_nodes = [n for n in component if G.nodes[n].get("entity_type") == "customer"]
        if len(customer_nodes) < 2:
            continue

        comp_txns = pd.concat([txn_by_customer.get_group(c) for c in customer_nodes if c in txn_by_customer.groups])
        if comp_txns.empty:
            continue

        merchant_id = comp_txns["merchant_id"].mode().iloc[0]
        baseline = merch.loc[merchant_id]
        return_rate = comp_txns["is_returned"].mean()
        dispute_rate = comp_txns["is_disputed"].mean()
        return_ratio = return_rate / max(baseline["baseline_return_rate"], 1e-4)
        dispute_ratio = dispute_rate / max(baseline["baseline_chargeback_rate"], 1e-4)
        outcome_signal = min(max(return_ratio, dispute_ratio) / 5.0, 1.0)

        ts = pd.to_datetime(comp_txns["timestamp"])
        span_days = max((ts.max() - ts.min()).total_seconds() / 86400.0, 0.25)
        txns_per_day = len(comp_txns) / span_days
        burst_signal = min(txns_per_day / 10.0, 1.0)  # >=10 txns/day within a cluster reads as fully bursty

        size_signal = min(np.log1p(len(customer_nodes)) / np.log1p(30), 1.0)

        graph_risk_score = 0.5 * outcome_signal + 0.35 * burst_signal + 0.15 * size_signal

        rows.append({
            "component_id": comp_id,
            "merchant_id": merchant_id,
            "customer_count": len(customer_nodes),
            "device_count": sum(1 for n in component if G.nodes[n].get("entity_type") == "device"),
            "address_count": sum(1 for n in component if G.nodes[n].get("entity_type") == "address"),
            "transaction_count": len(comp_txns),
            "return_rate": round(float(return_rate), 3),
            "dispute_rate": round(float(dispute_rate), 3),
            "return_rate_ratio": round(float(return_ratio), 2),
            "dispute_rate_ratio": round(float(dispute_ratio), 2),
            "span_days": round(float(span_days), 2),
            "txns_per_day": round(float(txns_per_day), 2),
            "graph_risk_score": round(float(graph_risk_score), 4),
            "customer_ids": sorted(customer_nodes),
        })

    return pd.DataFrame(rows).sort_values("graph_risk_score", ascending=False).reset_index(drop=True)


def score_transactions(transactions: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    """Broadcasts each component's graph_risk_score to its member transactions (0 if unclustered)."""
    cust_to_score = {}
    for row in components.itertuples(index=False):
        for c in row.customer_ids:
            cust_to_score[c] = max(cust_to_score.get(c, 0.0), row.graph_risk_score)
    out = transactions[["transaction_id", "customer_id"]].copy()
    out["graph_risk_score"] = out["customer_id"].map(cust_to_score).fillna(0.0)
    return out


if __name__ == "__main__":
    import json
    from ml.evaluation import classification_report

    entities = pd.read_csv(DATA_DIR / "entities.csv")
    relationships = pd.read_csv(DATA_DIR / "relationships.csv")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    merchants = pd.read_csv(DATA_DIR / "merchants.csv")
    labels = pd.read_csv(DATA_DIR / "ground_truth" / "transaction_labels.csv")

    G = build_graph(entities, relationships)
    print(f"Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges, "
          f"{nx.number_connected_components(G):,} connected components")

    components = score_components(G, transactions, merchants)
    print(f"Qualifying components (>=2 customers): {len(components)}")

    txn_scores = score_transactions(transactions, components)
    merged = txn_scores.merge(labels, on="transaction_id").merge(
        transactions[["transaction_id", "split"]], on="transaction_id",
    )

    print("\n=== Mean graph_risk_score by scenario_type (test split) ===")
    test = merged[merged["split"] == "test"]
    print(test.groupby("scenario_type")["graph_risk_score"].agg(["count", "mean", "max"]).sort_values("mean", ascending=False))

    print("\n=== Held-out precision/recall of graph_risk_score alone (test split) ===")
    for thresh in [0.3, 0.4, 0.5]:
        report = classification_report(test["is_fraud"].astype(int).to_numpy(), test["graph_risk_score"].to_numpy(), thresh)
        print(thresh, json.dumps(report))

    top = components.head(8)[[
        "component_id", "merchant_id", "customer_count", "device_count", "address_count",
        "return_rate_ratio", "dispute_rate_ratio", "span_days", "txns_per_day", "graph_risk_score",
    ]]
    print("\n=== Top 8 highest-risk components ===")
    print(top.to_string(index=False))

    ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
    ARTIFACT_DIR.mkdir(exist_ok=True)
    components.drop(columns=["customer_ids"]).to_csv(ARTIFACT_DIR / "graph_components.csv", index=False)
    txn_scores.to_csv(ARTIFACT_DIR / "graph_transaction_scores.csv", index=False)
