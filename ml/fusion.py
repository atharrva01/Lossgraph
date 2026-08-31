"""
Risk Fusion -- combines the three engines' independent scores into one
per-transaction probability estimate, via noisy-OR rather than a fourth
trained model:

    P_fused = 1 - (1 - P_transaction) * (1 - P_graph) * (1 - P_anomaly)

Noisy-OR is the right shape for this: any single strongly corroborating
signal should be enough to raise suspicion, and the estimate should only
stay low when ALL THREE engines independently see nothing. It's also fully
interpretable -- a judge (or a merchant ops analyst) can see exactly which
engine drove a given transaction's fused score, which a learned stacking
model would obscure.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

ANOMALY_Z_SCALE = 7.0  # z == Z_THRESHOLD (3.5) maps to ~0.5, z == 7 maps to ~1.0

# The anomaly score is merchant-DAY-level -- every transaction that merchant
# saw that day gets the same value, whether or not it had anything to do
# with whatever caused the day to look unusual. Combined via unweighted
# noisy-OR, that coarseness bleeds a day's anomaly into every unrelated
# transaction on it (verified empirically: without this weight, some
# `normal`-labelled test transactions hit a fused score of 1.0 purely from
# a same-day anomaly). Down-weighting its contribution keeps it a
# corroborating signal rather than a standalone accusation -- the graph and
# transaction engines stay at full weight since they're evidence about the
# specific transaction/customer, not the whole merchant that day.
ANOMALY_FUSION_WEIGHT = 0.5


def anomaly_probability(daily: pd.DataFrame) -> pd.DataFrame:
    """One row per (merchant_id, date) with a squashed [0,1] anomaly score."""
    z = daily[["z_return_rate", "z_dispute_rate"]].fillna(0).max(axis=1).clip(lower=0)
    out = daily[["merchant_id", "date"]].copy()
    out["anomaly_score"] = np.clip(z / ANOMALY_Z_SCALE, 0, 1)
    return out


def build_fused_scores(transactions: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per test-split transaction with all four scores plus
    the fused probability and its component_id (for grouping into cluster
    events -- -1 if the transaction's customer isn't in any qualifying
    graph component)."""
    risk = pd.read_csv(ARTIFACT_DIR / "test_risk_scores.csv")
    graph = pd.read_csv(ARTIFACT_DIR / "graph_transaction_scores.csv")
    daily = pd.read_csv(ARTIFACT_DIR / "merchant_daily_anomaly.csv", parse_dates=["date"])

    df = transactions[transactions["split"] == "test"].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["order_date"] = df["timestamp"].dt.floor("D")

    df = df.merge(risk, on="transaction_id", how="left")
    df = df.merge(graph[["transaction_id", "graph_risk_score", "component_id"]], on="transaction_id", how="left")

    anomaly = anomaly_probability(daily)
    df = df.merge(
        anomaly, left_on=["merchant_id", "order_date"], right_on=["merchant_id", "date"], how="left",
    )

    df["risk_score"] = df["risk_score"].fillna(0.0)
    df["graph_risk_score"] = df["graph_risk_score"].fillna(0.0)
    df["component_id"] = df["component_id"].fillna(-1).astype(int)
    df["anomaly_score"] = df["anomaly_score"].fillna(0.0)

    weighted_anomaly = df["anomaly_score"] * ANOMALY_FUSION_WEIGHT
    df["fused_score"] = 1 - (1 - df["risk_score"]) * (1 - df["graph_risk_score"]) * (1 - weighted_anomaly)
    return df


if __name__ == "__main__":
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    fused = build_fused_scores(transactions)
    ARTIFACT_DIR.mkdir(exist_ok=True)
    fused.to_csv(ARTIFACT_DIR / "fused_scores.csv", index=False)
    print(f"Fused {len(fused):,} test-split transactions.")
    print(fused[["risk_score", "graph_risk_score", "anomaly_score", "fused_score"]].describe())
