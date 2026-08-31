"""
Baseline (normal) transaction behaviour generation.

Produces one transaction stream per customer as a Poisson process modulated
by weekly/diurnal seasonality, plus post-transaction outcomes (return,
refund, chargeback) drawn from merchant baselines and customer propensities.

Every transaction/outcome produced here is legitimate (scenario.py injects
the loss processes separately and independently labels them).
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from .config import PAYMENT_METHODS, TimeConfig

# Hand-tuned diurnal shape: low overnight, lunch bump, evening peak.
_DIURNAL_RAW = np.array([
    0.5, 0.3, 0.2, 0.15, 0.15, 0.2, 0.4, 0.8, 1.2, 1.5, 1.7, 1.9,
    2.2, 2.0, 1.6, 1.4, 1.5, 1.7, 2.0, 2.4, 2.6, 2.3, 1.6, 0.9,
])
DIURNAL_WEIGHTS = _DIURNAL_RAW / _DIURNAL_RAW.sum()

DISPUTE_REASONS = ["non_receipt", "not_as_described", "unauthorized", "duplicate_charge", "quality_issue"]


def _sample_seconds_of_day(rng: np.random.Generator, n: int) -> np.ndarray:
    hours = rng.choice(24, size=n, p=DIURNAL_WEIGHTS)
    minutes = rng.integers(0, 60, size=n)
    seconds = rng.integers(0, 60, size=n)
    return hours * 3600 + minutes * 60 + seconds


def _weighted_day_offsets(active_days: int, start_date, rng: np.random.Generator, n: int) -> np.ndarray:
    day_indices = np.arange(active_days)
    weekdays = [(start_date + timedelta(days=int(d))).weekday() for d in day_indices]
    weights = np.array([1.25 if wd >= 5 else 1.0 for wd in weekdays], dtype=float)
    weights /= weights.sum()
    return rng.choice(day_indices, size=n, p=weights)


def generate_baseline_transactions(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    addresses: pd.DataFrame,
    time_config: TimeConfig,
    rng: np.random.Generator,
) -> pd.DataFrame:
    merchants_by_id = merchants.set_index("merchant_id")

    products_by_merchant = {
        mid: grp[["product_id", "price"]].reset_index(drop=True)
        for mid, grp in products.groupby("merchant_id")
    }

    end_date = pd.Timestamp(time_config.end_date)
    start_date = time_config.start_date

    rows = []
    txn_counter = 0

    for cust in customers.itertuples(index=False):
        active_start_date = max(cust.created_at.date(), start_date)
        active_start = pd.Timestamp(active_start_date)
        active_days = (time_config.end_date - active_start_date).days
        if active_days <= 0:
            continue

        merchant = merchants_by_id.loc[cust.merchant_id]
        expected_orders = cust.activity_level * (active_days / 7.0)
        n_orders = rng.poisson(max(expected_orders, 0.01))
        if n_orders == 0:
            continue

        day_offsets = _weighted_day_offsets(active_days, active_start_date, rng, n_orders)
        sod = _sample_seconds_of_day(rng, n_orders)
        timestamps = [active_start + timedelta(days=int(d), seconds=int(s)) for d, s in zip(day_offsets, sod)]

        cat_products = products_by_merchant.get(cust.merchant_id)
        if cat_products is None or len(cat_products) == 0:
            continue
        prod_weights = 1.0 / np.sqrt(cat_products["price"].to_numpy())
        prod_weights /= prod_weights.sum()
        chosen_products = rng.choice(len(cat_products), size=n_orders, p=prod_weights)
        quantities = rng.choice([1, 1, 1, 2, 2, 3], size=n_orders)

        # Rare on purpose: at demo-scale pool sizes, a uniform-random switch is a
        # long-range edge in the identity graph. Too high a rate and the whole
        # baseline population percolates into one giant connected component,
        # which would make every legitimate cluster indistinguishable from a
        # ring. Real populations are this sparse -- most people use their own
        # device essentially all the time.
        use_home_device = rng.random(n_orders) < 0.99
        use_home_address = rng.random(n_orders) < 0.98
        use_preferred_payment = rng.random(n_orders) < 0.85

        random_payments = rng.choice(PAYMENT_METHODS, size=n_orders)

        return_p = np.clip(merchant.baseline_return_rate * cust.return_propensity, 0, 0.9)
        refund_only_p = np.clip(merchant.baseline_refund_only_rate * cust.return_propensity, 0, 0.5)
        chargeback_p = np.clip(merchant.baseline_chargeback_rate * cust.chargeback_propensity, 0, 0.5)

        is_returned = rng.random(n_orders) < return_p
        is_refund_only = (~is_returned) & (rng.random(n_orders) < refund_only_p)
        is_refunded = is_returned | is_refund_only

        base_dispute_roll = rng.random(n_orders)
        dispute_threshold = np.where(is_refunded, chargeback_p * 0.3, chargeback_p)
        is_disputed = base_dispute_roll < dispute_threshold

        for i in range(n_orders):
            prod = cat_products.iloc[chosen_products[i]]
            order_time = timestamps[i]
            amount = round(float(prod["price"]) * int(quantities[i]) * float(rng.uniform(0.95, 1.08)), 2)

            returned_at = order_time + timedelta(days=int(rng.integers(1, 15))) if is_returned[i] else None
            if is_returned[i]:
                refunded_at = returned_at + timedelta(days=int(rng.integers(0, 4)))
            elif is_refund_only[i]:
                refunded_at = order_time + timedelta(days=int(rng.integers(1, 11)))
            else:
                refunded_at = None
            disputed_at = (
                order_time + timedelta(days=int(rng.integers(7, 76))) if is_disputed[i] else None
            )

            txn_counter += 1
            rows.append({
                "transaction_id": f"TXN-{txn_counter:08d}",
                "merchant_id": cust.merchant_id,
                "customer_id": cust.customer_id,
                "amount": amount,
                "timestamp": order_time,
                "payment_method": cust.preferred_payment_method if use_preferred_payment[i] else random_payments[i],
                # A one-off device/address (never reused) rather than a draw from the
                # shared pool: models "used a friend's phone / a cybercafe once"
                # without creating an incidental edge to some unrelated customer.
                "device_id": cust.home_device_id if use_home_device[i] else f"DEV-ONESHOT-{txn_counter}",
                "address_id": cust.home_address_id if use_home_address[i] else f"ADDR-ONESHOT-{txn_counter}",
                "product_id": prod["product_id"],
                "status": "approved",
                "is_returned": bool(is_returned[i]),
                "returned_at": returned_at,
                "is_refunded": bool(is_refunded[i]),
                "refunded_at": refunded_at,
                "is_disputed": bool(is_disputed[i]),
                "disputed_at": disputed_at,
                "dispute_reason": rng.choice(DISPUTE_REASONS) if is_disputed[i] else None,
                "is_fraud": False,
                "scenario_id": None,
                "scenario_type": "normal",
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df[df["timestamp"] < end_date].reset_index(drop=True)
    return df
