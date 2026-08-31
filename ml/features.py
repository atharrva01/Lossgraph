"""
Leakage-safe feature engineering for the transaction risk model (Engine 1).

Every feature here is computable at authorization time -- the instant the
transaction happens -- using only:
  - the transaction's own static attributes (amount, time, payment method)
  - aggregates over that customer/device/address's PRIOR transactions
    (strictly earlier timestamp, via shift(1)/running-count-before)

None of the post-transaction outcome columns (is_returned, is_disputed,
status, *_at) are used for the row they belong to. They ARE used, lagged,
to build history features for later rows -- exactly how a real risk engine
observes outcomes as they arrive and folds them into the next score.
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "amount", "log_amount", "amount_vs_merchant_avg",
    "hour_of_day", "day_of_week", "is_weekend",
    "customer_prior_txn_count", "customer_days_since_created",
    "customer_prior_avg_amount", "customer_prior_return_rate", "customer_prior_dispute_rate",
    "device_customer_count_prior", "device_txn_count_prior",
    "address_customer_count_prior", "address_txn_count_prior",
    "is_home_device", "is_home_address",
    "payment_method", "merchant_id",
]
CATEGORICAL_COLUMNS = ["payment_method", "merchant_id"]


def _running_distinct_count_prior(sub: pd.DataFrame, col: str) -> pd.Series:
    seen = set()
    out = np.empty(len(sub), dtype=np.int32)
    for i, val in enumerate(sub[col].to_numpy()):
        out[i] = len(seen)
        seen.add(val)
    return pd.Series(out, index=sub.index)


def _running_count_prior(sub: pd.DataFrame) -> pd.Series:
    return pd.Series(np.arange(len(sub)), index=sub.index)


def build_features(transactions: pd.DataFrame, customers: pd.DataFrame, merchants: pd.DataFrame) -> pd.DataFrame:
    df = transactions.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    cust = customers.set_index("customer_id")
    df["_customer_created_at"] = pd.to_datetime(df["customer_id"].map(cust["created_at"]))
    df["_home_device_id"] = df["customer_id"].map(cust["home_device_id"])
    df["_home_address_id"] = df["customer_id"].map(cust["home_address_id"])

    merch = merchants.set_index("merchant_id")
    df["_merchant_avg_order_value"] = df["merchant_id"].map(merch["avg_order_value"])
    df["_merchant_baseline_return_rate"] = df["merchant_id"].map(merch["baseline_return_rate"])
    df["_merchant_baseline_chargeback_rate"] = df["merchant_id"].map(merch["baseline_chargeback_rate"])

    df["log_amount"] = np.log1p(df["amount"])
    df["amount_vs_merchant_avg"] = df["amount"] / df["_merchant_avg_order_value"].replace(0, np.nan)
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_home_device"] = (df["device_id"] == df["_home_device_id"]).astype(int)
    df["is_home_address"] = (df["address_id"] == df["_home_address_id"]).astype(int)

    cust_grp = df.groupby("customer_id", group_keys=False)
    df["customer_prior_txn_count"] = cust_grp.apply(_running_count_prior)
    df["customer_days_since_created"] = (df["timestamp"] - df["_customer_created_at"]).dt.total_seconds() / 86400.0
    df["customer_prior_avg_amount"] = cust_grp["amount"].transform(lambda s: s.shift(1).expanding().mean())
    df["customer_prior_return_rate"] = cust_grp["is_returned"].transform(lambda s: s.shift(1).expanding().mean())
    df["customer_prior_dispute_rate"] = cust_grp["is_disputed"].transform(lambda s: s.shift(1).expanding().mean())

    # Cold start: no prior history -> fall back to merchant baseline (section 35).
    df["customer_prior_avg_amount"] = df["customer_prior_avg_amount"].fillna(df["_merchant_avg_order_value"])
    df["customer_prior_return_rate"] = df["customer_prior_return_rate"].fillna(df["_merchant_baseline_return_rate"])
    df["customer_prior_dispute_rate"] = df["customer_prior_dispute_rate"].fillna(df["_merchant_baseline_chargeback_rate"])

    device_grp = df.groupby("device_id", group_keys=False)
    df["device_customer_count_prior"] = device_grp.apply(lambda g: _running_distinct_count_prior(g, "customer_id"))
    df["device_txn_count_prior"] = device_grp.apply(_running_count_prior)

    address_grp = df.groupby("address_id", group_keys=False)
    df["address_customer_count_prior"] = address_grp.apply(lambda g: _running_distinct_count_prior(g, "customer_id"))
    df["address_txn_count_prior"] = address_grp.apply(_running_count_prior)

    df["payment_method"] = df["payment_method"].astype("category")
    df["merchant_id"] = df["merchant_id"].astype("category")

    keep = ["transaction_id", "timestamp", "split"] + FEATURE_COLUMNS
    return df[keep]
