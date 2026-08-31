"""
Baseline entity generation: merchants, products, devices, addresses, customers.

Everything here produces the *legitimate* population. Scenario injection
(scenarios.py) layers additional customers/transactions on top and is
responsible for all ground-truth fraud/abuse labels.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from .config import (
    BASELINE_CHARGEBACK_RATE_RANGE,
    BASELINE_FRAUD_RATE_RANGE,
    BASELINE_REFUND_ONLY_RATE_RANGE,
    BASELINE_RETURN_RATE_RANGE,
    MERCHANT_CATEGORIES,
    PAYMENT_METHODS,
    ScaleConfig,
    TimeConfig,
)

CITIES = [
    ("Mumbai", "west"), ("Pune", "west"), ("Ahmedabad", "west"),
    ("Bengaluru", "south"), ("Chennai", "south"), ("Hyderabad", "south"),
    ("Delhi", "north"), ("Jaipur", "north"), ("Lucknow", "north"),
    ("Kolkata", "east"), ("Bhubaneswar", "east"), ("Guwahati", "east"),
]

CATEGORY_AOV = {  # mean average order value by merchant category
    "electronics": 8500.0,
    "fashion": 2200.0,
    "grocery": 900.0,
    "home_goods": 3200.0,
    "beauty": 1400.0,
}

DEVICE_TYPES = ["mobile", "desktop", "tablet"]
DEVICE_TYPE_WEIGHTS = [0.68, 0.27, 0.05]

SEGMENT_WEIGHTS = {"new": 0.15, "regular": 0.70, "high_value": 0.15}


def generate_merchants(scale: ScaleConfig, rng: np.random.Generator) -> pd.DataFrame:
    n = scale.n_merchants
    categories = rng.choice(MERCHANT_CATEGORIES, size=n)
    rows = []
    for i in range(n):
        cat = categories[i]
        rows.append({
            "merchant_id": f"M{i + 1:03d}",
            "name": f"{cat.title().replace('_', ' ')} Store {i + 1}",
            "category": cat,
            "avg_order_value": float(CATEGORY_AOV[cat] * rng.uniform(0.8, 1.25)),
            "baseline_return_rate": float(rng.uniform(*BASELINE_RETURN_RATE_RANGE)),
            "baseline_refund_only_rate": float(rng.uniform(*BASELINE_REFUND_ONLY_RATE_RANGE)),
            "baseline_chargeback_rate": float(rng.uniform(*BASELINE_CHARGEBACK_RATE_RANGE)),
            "baseline_fraud_rate": float(rng.uniform(*BASELINE_FRAUD_RATE_RANGE)),
            "risk_tolerance": rng.choice(["conservative", "moderate", "aggressive"], p=[0.3, 0.5, 0.2]),
            "false_positive_cost": float(rng.uniform(150, 800)),
            "verification_cost": float(rng.uniform(15, 60)),
            "avg_fraud_loss": float(CATEGORY_AOV[cat] * rng.uniform(1.5, 3.5)),
        })
    return pd.DataFrame(rows)


def generate_products(scale: ScaleConfig, merchants: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = scale.n_products
    merchant_ids = merchants["merchant_id"].to_numpy()
    merchant_cat = merchants.set_index("merchant_id")["category"].to_dict()
    merchant_aov = merchants.set_index("merchant_id")["avg_order_value"].to_dict()

    assigned_merchants = rng.choice(merchant_ids, size=n)
    is_viral = rng.random(n) < 0.01  # ~1% of catalogue are "could go viral" candidates

    rows = []
    for i in range(n):
        mid = assigned_merchants[i]
        cat = merchant_cat[mid]
        price = max(99.0, float(rng.lognormal(mean=np.log(merchant_aov[mid] * 0.6), sigma=0.6)))
        rows.append({
            "product_id": f"SKU-{i + 1:05d}",
            "sku": f"SKU-{i + 1:05d}",
            "merchant_id": mid,
            "category": cat,
            "price": round(price, 2),
            "is_viral_candidate": bool(is_viral[i]),
        })
    return pd.DataFrame(rows)


def generate_devices(scale: ScaleConfig, time_config: TimeConfig, rng: np.random.Generator) -> pd.DataFrame:
    n = scale.n_devices
    device_types = rng.choice(DEVICE_TYPES, size=n, p=DEVICE_TYPE_WEIGHTS)
    created_offsets = rng.integers(-540, time_config.total_days, size=n)
    rows = []
    for i in range(n):
        rows.append({
            "device_id": f"DEV-{i + 1:06d}",
            "device_type": device_types[i],
            "created_at": pd.Timestamp(time_config.start_date) + timedelta(days=int(created_offsets[i])),
        })
    return pd.DataFrame(rows)


def generate_addresses(scale: ScaleConfig, time_config: TimeConfig, rng: np.random.Generator) -> pd.DataFrame:
    n = scale.n_addresses
    city_idx = rng.integers(0, len(CITIES), size=n)
    created_offsets = rng.integers(-540, time_config.total_days, size=n)
    rows = []
    for i in range(n):
        city, region = CITIES[city_idx[i]]
        rows.append({
            "address_id": f"ADDR-{i + 1:06d}",
            "city": city,
            "region": region,
            "created_at": pd.Timestamp(time_config.start_date) + timedelta(days=int(created_offsets[i])),
        })
    return pd.DataFrame(rows)


def generate_customers(
    scale: ScaleConfig,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    addresses: pd.DataFrame,
    time_config: TimeConfig,
    rng: np.random.Generator,
) -> pd.DataFrame:
    n = scale.n_customers
    merchant_ids = merchants["merchant_id"].to_numpy()
    device_ids = devices["device_id"].to_numpy()
    address_ids = addresses["address_id"].to_numpy()

    assigned_merchants = rng.choice(merchant_ids, size=n)
    # replace=False: home assignment is collision-free by construction, so
    # baseline graph sparsity doesn't depend on getting pool-size-vs-customer
    # ratios "right" -- the only customer-customer edges come from the
    # explicit, rate-controlled pairing injected below and from scenario
    # cohorts, never from incidental birthday-paradox collisions.
    home_devices = rng.choice(device_ids, size=n, replace=False)
    home_addresses = rng.choice(address_ids, size=n, replace=False)
    payment_prefs = rng.choice(PAYMENT_METHODS, size=n, p=[0.45, 0.35, 0.12, 0.08])
    segments = rng.choice(list(SEGMENT_WEIGHTS.keys()), size=n, p=list(SEGMENT_WEIGHTS.values()))

    # 80% established (joined before the observation window), 20% organic signups during it.
    established = rng.random(n) < 0.8
    join_offsets = np.where(
        established,
        -rng.integers(1, 400, size=n),
        rng.integers(0, time_config.total_days, size=n),
    )

    # Behavioral propensities: multiplicative factors around 1.0 applied to merchant baselines.
    return_propensity = rng.lognormal(mean=0.0, sigma=0.5, size=n)
    chargeback_propensity = rng.lognormal(mean=0.0, sigma=0.6, size=n)
    activity_level = rng.gamma(shape=2.0, scale=0.5, size=n)  # baseline orders/week

    rows = []
    for i in range(n):
        rows.append({
            "customer_id": f"CUST-{i + 1:06d}",
            "merchant_id": assigned_merchants[i],
            "created_at": pd.Timestamp(time_config.start_date) + timedelta(days=int(join_offsets[i])),
            "segment": segments[i],
            "home_device_id": home_devices[i],
            "home_address_id": home_addresses[i],
            "preferred_payment_method": payment_prefs[i],
            "return_propensity": float(return_propensity[i]),
            "chargeback_propensity": float(chargeback_propensity[i]),
            "activity_level": float(activity_level[i]),
            "true_archetype": "legit",
            "scenario_id": None,
        })
    df = pd.DataFrame(rows)

    # Controlled natural sharing: a small, fixed-rate fraction of customers
    # (siblings, couples) genuinely share a device/address. Rate is fixed
    # regardless of scale, so it never risks percolating into a giant
    # component the way pool-size-dependent random collision would.
    df = _inject_natural_pairs(df, "home_device_id", rate=0.03, rng=rng)
    df = _inject_natural_pairs(df, "home_address_id", rate=0.025, rng=rng)
    return df


def _inject_natural_pairs(df: pd.DataFrame, column: str, rate: float, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    n_followers = int(n * rate)
    if n_followers == 0:
        return df
    follower_idx = rng.choice(n, size=n_followers, replace=False)
    leader_idx = rng.integers(0, n, size=n_followers)
    values = df[column].to_numpy(copy=True)
    values[follower_idx] = values[leader_idx]
    df[column] = values
    return df
