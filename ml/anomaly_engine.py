"""
Engine 4 -- Merchant Temporal Anomaly Engine.

Tracks daily return/dispute/order-volume series per merchant and flags days
where a rate deviates from its own trailing baseline (rolling z-score) --
the section 15 EWMA/CUSUM-style approach, kept to a rolling z-score for
transparency (a raw statistical deviation is easier to defend to a judge
than a fitted change-point model, and at this data scale gives basically
the same answer).

This engine watches the OUTCOME stream (returns/disputes as they land, not
orders as they're placed) -- it is explicitly not a real-time,
pre-authorization score, unlike Engine 1. It is exactly what makes
chargeback_wave detectable at all, since that scenario has zero
transaction-time signal by construction.

Critically: this engine cannot tell a genuine loss event (fraud_spike,
chargeback_wave, coordinated_return_ring) from a legitimate rate/volume
change (seasonal_return_spike, promotional_campaign_spike) -- both produce
real statistical deviations. That disambiguation needs the graph engine's
cluster-structure signal, which is exactly why loss-event detection (day 3)
fuses this with graph_engine.py rather than acting on either alone.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"

ROLLING_WINDOW = 14
MIN_PERIODS = 7
Z_THRESHOLD = 3.5


def _full_date_index(transactions: pd.DataFrame) -> pd.DatetimeIndex:
    start = pd.to_datetime(transactions["timestamp"]).dt.floor("D").min()
    end = pd.to_datetime(transactions["timestamp"]).dt.floor("D").max()
    return pd.date_range(start, end, freq="D")


def build_daily_series(transactions: pd.DataFrame) -> pd.DataFrame:
    df = transactions.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["returned_at"] = pd.to_datetime(df["returned_at"])
    df["disputed_at"] = pd.to_datetime(df["disputed_at"])

    dates = _full_date_index(df)
    merchants = df["merchant_id"].unique()
    full_index = pd.MultiIndex.from_product([merchants, dates], names=["merchant_id", "date"])

    orders = df.assign(date=df["timestamp"].dt.floor("D")).groupby(["merchant_id", "date"]).size()
    returns = (
        df.dropna(subset=["returned_at"]).assign(date=lambda d: d["returned_at"].dt.floor("D"))
        .groupby(["merchant_id", "date"]).size()
    )
    disputes = (
        df.dropna(subset=["disputed_at"]).assign(date=lambda d: d["disputed_at"].dt.floor("D"))
        .groupby(["merchant_id", "date"]).size()
    )

    out = pd.DataFrame(index=full_index)
    out["order_count"] = orders.reindex(full_index, fill_value=0)
    out["return_count"] = returns.reindex(full_index, fill_value=0)
    out["dispute_count"] = disputes.reindex(full_index, fill_value=0)
    out = out.reset_index()

    safe_orders = out["order_count"].replace(0, np.nan)
    out["return_rate"] = (out["return_count"] / safe_orders).fillna(0.0)
    out["dispute_rate"] = (out["dispute_count"] / safe_orders).fillna(0.0)
    return out


def _poisson_zscore(count: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Variance-stabilized z-score for a daily count relative to a POOLED
    trailing baseline rate: expected(d) = baseline_rate(d) * volume(d),
    z(d) = (count(d) - expected(d)) / sqrt(expected(d)).

    A naive z-score on the daily *ratio* (count/volume) is what we started
    with, and it false-alarms constantly on quiet merchant-days: a 40-order
    day with 6 returns is a 15% "return rate" that looks wild next to a 3%
    baseline, but 6 vs an expected ~1.2 is unremarkable Poisson noise at that
    volume. Pooling the trailing baseline over raw counts (not averaging
    daily ratios) and normalizing by sqrt(expected) fixes both problems at
    once -- it's the standard fix for "control chart on a rare-event rate."
    """
    trailing_count = count.shift(1).rolling(ROLLING_WINDOW, min_periods=MIN_PERIODS).sum()
    trailing_volume = volume.shift(1).rolling(ROLLING_WINDOW, min_periods=MIN_PERIODS).sum()
    baseline_rate = trailing_count / trailing_volume.replace(0, np.nan)
    expected = baseline_rate * volume
    return (count - expected) / np.sqrt(expected.clip(lower=1.0))


def add_anomaly_scores(daily: pd.DataFrame) -> pd.DataFrame:
    daily = daily.sort_values(["merchant_id", "date"]).reset_index(drop=True)
    out = []
    for merchant_id, grp in daily.groupby("merchant_id"):
        grp = grp.copy()
        grp["z_return_rate"] = _poisson_zscore(grp["return_count"], grp["order_count"])
        grp["z_dispute_rate"] = _poisson_zscore(grp["dispute_count"], grp["order_count"])
        out.append(grp)
    daily = pd.concat(out, ignore_index=True)
    daily["is_anomalous"] = (
        (daily["z_return_rate"] >= Z_THRESHOLD) | (daily["z_dispute_rate"] >= Z_THRESHOLD)
    ).fillna(False)
    return daily



# How long after a scenario's own window an outcome-driven anomaly can still
# fairly be attributed to it, sized from that scenario's own dispute/return
# delay parameters in scenarios.py (not a generic guess): ring/fraud_spike
# disputes land 5-40 days out, chargeback_wave and seasonal_return_spike flip
# outcomes immediately within their own window (near-zero extra lag needed).
LOOKAHEAD_DAYS = {
    "coordinated_return_ring": 25,
    "fraud_spike": 45,
    "chargeback_wave": 3,
    "seasonal_return_spike": 3,
    "false_positive_trap": 14,
    "household_address_sharing": 14,
    "corporate_device_sharing": 14,
    "viral_product_spike": 14,
    "new_customer_cold_start": 14,
    "promotional_campaign_spike": 14,
}


if __name__ == "__main__":
    import json

    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    manifest = json.load(open(DATA_DIR / "ground_truth" / "scenario_manifest.json"))

    daily = build_daily_series(transactions)
    daily = add_anomaly_scores(daily)

    ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
    ARTIFACT_DIR.mkdir(exist_ok=True)
    daily.to_csv(ARTIFACT_DIR / "merchant_daily_anomaly.csv", index=False)

    print(f"Daily series: {len(daily):,} merchant-days, {int(daily['is_anomalous'].sum())} flagged as anomalous "
          f"(z >= {Z_THRESHOLD})\n")

    print("=== Detection recall + latency per scenario type (all splits) ===")
    rows = []
    for m in manifest:
        merchant_id = m["merchant_id"]
        onset = pd.to_datetime(m["true_onset"]).floor("D")
        window_end = pd.to_datetime(m["window_end"]).floor("D")
        lookahead_end = window_end + pd.Timedelta(days=LOOKAHEAD_DAYS.get(m["scenario_type"], 14))
        flags = daily[
            (daily["merchant_id"] == merchant_id) & daily["is_anomalous"]
            & (daily["date"] >= onset) & (daily["date"] <= lookahead_end)
        ]
        detected = len(flags) > 0
        delay_days = (flags["date"].min() - onset).days if detected else None
        rows.append({
            "event_id": m["event_id"], "scenario_type": m["scenario_type"], "category": m["category"],
            "split": m["split"], "detected": detected, "delay_days": delay_days,
            "exposure_estimate": m["exposure_estimate"],
        })
    det = pd.DataFrame(rows)
    summary = det.groupby(["category", "scenario_type"]).agg(
        n=("detected", "count"), detected=("detected", "sum"),
        detection_rate=("detected", "mean"), mean_delay_days=("delay_days", "mean"),
    ).round(2)
    print(summary)

    test_loss = det[(det["split"] == "test") & (det["category"] == "loss")]
    print(f"\nTest-split loss-event detection recall: {test_loss['detected'].mean():.2%} "
          f"({int(test_loss['detected'].sum())}/{len(test_loss)}), "
          f"mean delay {test_loss['delay_days'].mean():.1f} days")

    det.to_csv(ARTIFACT_DIR / "anomaly_detection_report.csv", index=False)
