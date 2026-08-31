"""Shared context object passed into every scenario injector."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from .scenarios import IdCounters


@dataclass
class ScenarioContext:
    merchants: pd.DataFrame
    products: pd.DataFrame
    device_pool: np.ndarray
    address_pool: np.ndarray
    existing_customers: pd.DataFrame
    baseline_transactions: pd.DataFrame
    ids: IdCounters
    window_start: pd.Timestamp
    window_end: pd.Timestamp
    split: str

    def pick_merchant(self, rng: np.random.Generator):
        return self.merchants.sample(n=1, random_state=int(rng.integers(0, 2**31 - 1))).iloc[0]

    def random_start(self, rng: np.random.Generator, duration_hours: float, min_lookback_days: int = 0) -> pd.Timestamp:
        earliest = self.window_start + timedelta(days=min_lookback_days)
        latest = self.window_end - timedelta(hours=duration_hours)
        if latest <= earliest:
            latest = earliest + timedelta(seconds=1)
        span = int((latest - earliest).total_seconds())
        offset = int(rng.integers(0, max(span, 1)))
        return earliest + timedelta(seconds=offset)

    def manifest_entry(self, event_id, scenario_type, category, merchant_id, start, end, txns, cohort_df, exposure, params, description):
        if len(txns):
            affected_customers = sorted(set(txns["customer_id"].dropna()))
            affected_devices = sorted(set(txns["device_id"].dropna()))
            first_txn = txns["timestamp"].min()
            last_txn = txns["timestamp"].max()
        else:
            affected_customers = sorted(set(cohort_df["customer_id"].dropna())) if len(cohort_df) else []
            affected_devices = []
            first_txn = None
            last_txn = None
        return {
            "event_id": event_id,
            "scenario_type": scenario_type,
            "category": category,
            "merchant_id": merchant_id,
            "split": self.split,
            "true_onset": start.isoformat(),
            "window_end": end.isoformat(),
            "first_transaction_time": first_txn.isoformat() if first_txn is not None else None,
            "last_transaction_time": last_txn.isoformat() if last_txn is not None else None,
            "affected_transaction_count": int(len(txns)),
            "affected_customer_count": len(affected_customers),
            "affected_device_count": len(affected_devices),
            "affected_customer_ids": affected_customers,
            "exposure_estimate": round(float(exposure), 2),
            "params": params,
            "description": description,
        }
