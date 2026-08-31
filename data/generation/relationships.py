"""
Builds the entity/relationship tables the graph engine consumes, derived
purely from the transaction stream (exactly how a real ingestion pipeline
would build them -- nothing here is scenario-aware).

Relationships are bipartite (customer -> device/address/product) rather than
pairwise customer-customer edges. This avoids O(n^2) edge blow-up on popular
shared devices; the graph engine derives customer clusters by projecting
this bipartite graph (e.g. connected components), which is both more
standard and more scalable than materializing every pairwise link here.
"""

import numpy as np
import pandas as pd


def build_entities(transactions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    frames = []

    cust_last_seen = transactions.groupby("customer_id")["timestamp"].max()
    cust_txn_count = transactions.groupby("customer_id")["timestamp"].count()
    cust = customers[["customer_id", "created_at"]].rename(columns={"customer_id": "entity_id", "created_at": "first_seen"})
    cust["entity_type"] = "customer"
    cust["last_seen"] = cust["entity_id"].map(cust_last_seen).fillna(cust["first_seen"])
    cust["transaction_count"] = cust["entity_id"].map(cust_txn_count).fillna(0).astype(int)
    frames.append(cust[["entity_id", "entity_type", "first_seen", "last_seen", "transaction_count"]])

    for col, entity_type in [("device_id", "device"), ("address_id", "address"), ("product_id", "product")]:
        agg = transactions.groupby(col)["timestamp"].agg(first_seen="min", last_seen="max", transaction_count="count").reset_index()
        agg = agg.rename(columns={col: "entity_id"})
        agg["entity_type"] = entity_type
        frames.append(agg[["entity_id", "entity_type", "first_seen", "last_seen", "transaction_count"]])

    entities = pd.concat(frames, ignore_index=True)
    entities = entities.dropna(subset=["entity_id"]).reset_index(drop=True)
    return entities


def build_relationships(transactions: pd.DataFrame) -> pd.DataFrame:
    edge_specs = [
        ("device_id", "USED_DEVICE"),
        ("address_id", "USED_ADDRESS"),
        ("product_id", "BOUGHT_PRODUCT"),
    ]
    frames = []
    for col, rel_type in edge_specs:
        sub = transactions.dropna(subset=[col])
        grp = sub.groupby(["customer_id", col, "merchant_id"])["timestamp"].agg(
            first_seen="min", last_seen="max", frequency="count",
        ).reset_index()
        grp = grp.rename(columns={"customer_id": "source_entity_id", col: "target_entity_id"})
        grp["relationship_type"] = rel_type
        frames.append(grp)

    relationships = pd.concat(frames, ignore_index=True)
    # Recency-aware confidence: more observations -> higher confidence, saturating quickly.
    relationships["confidence"] = np.round(1 - np.exp(-relationships["frequency"] / 3.0), 3)
    relationships.insert(0, "relationship_id", [f"REL-{i + 1:08d}" for i in range(len(relationships))])
    return relationships[[
        "relationship_id", "source_entity_id", "target_entity_id", "relationship_type",
        "first_seen", "last_seen", "frequency", "confidence", "merchant_id",
    ]]
