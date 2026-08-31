"""
Scenario injection: layers loss processes and legitimate-but-unusual edge
cases on top of the baseline transaction stream.

Every injector is independently labelled in the returned ground-truth
records. Labels are NEVER written into the feature columns models train on
(behavioural signals only) -- they live in a separate ground-truth table
assembled by labels.py, exactly as section 27/32 of the PRD requires.

Two families of injector:
  - "additive": spawn new customers + new transactions (ring, fraud spike,
    false-positive trap, and most section-34 edge cases).
  - "mutating": select existing baseline transactions and flip their outcome
    fields (chargeback wave, seasonal return spike). This models losses that
    surface *after* the fact, against transactions that already happened.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd

DISPUTE_REASONS_FRAUD = ["unauthorized", "duplicate_charge"]
DISPUTE_REASONS_ABUSE = ["not_as_described", "non_receipt", "quality_issue"]


@dataclass
class IdCounters:
    customer: int
    transaction: int
    device: int
    event: int

    def next_customer_id(self) -> str:
        self.customer += 1
        return f"CUST-{self.customer:06d}"

    def next_transaction_id(self) -> str:
        self.transaction += 1
        return f"TXN-{self.transaction:08d}"

    def next_device_id(self) -> str:
        self.device += 1
        return f"DEV-RING-{self.device:05d}"

    def next_event_id(self, year: int) -> str:
        self.event += 1
        return f"RE-{year}-{self.event:05d}"


TXN_COLUMNS = [
    "transaction_id", "merchant_id", "customer_id", "amount", "timestamp",
    "payment_method", "device_id", "address_id", "product_id", "status",
    "is_returned", "returned_at", "is_refunded", "refunded_at",
    "is_disputed", "disputed_at", "dispute_reason",
    "is_fraud", "scenario_id", "scenario_type",
]


def _spawn_cohort(
    n: int,
    merchant_id: str,
    created_at: pd.Timestamp,
    rng: np.random.Generator,
    ids: IdCounters,
    shared_devices: Optional[list] = None,
    shared_addresses: Optional[list] = None,
    device_pool: Optional[np.ndarray] = None,
    address_pool: Optional[np.ndarray] = None,
    payment_pref_pool=("card", "upi", "netbanking", "wallet"),
    segment: str = "new",
) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        if shared_devices:
            home_device = rng.choice(shared_devices)
        elif device_pool is not None:
            home_device = rng.choice(device_pool)
        else:
            home_device = None
        if shared_addresses:
            home_address = rng.choice(shared_addresses)
        elif address_pool is not None:
            home_address = rng.choice(address_pool)
        else:
            home_address = None
        rows.append({
            "customer_id": ids.next_customer_id(),
            "merchant_id": merchant_id,
            "created_at": created_at,
            "segment": segment,
            "home_device_id": home_device,
            "home_address_id": home_address,
            "preferred_payment_method": rng.choice(list(payment_pref_pool)),
            "return_propensity": 1.0,
            "chargeback_propensity": 1.0,
            "activity_level": 0.5,
            "true_archetype": segment,
            "scenario_id": None,  # filled in by caller
        })
    return pd.DataFrame(rows)


def _burst_transactions(
    customers: pd.DataFrame,
    merchant_row,
    products: pd.DataFrame,
    rng: np.random.Generator,
    ids: IdCounters,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    scenario_id: str,
    scenario_type: str,
    is_fraud: bool,
    orders_per_customer=(1, 2),
    amount_multiplier=(1.0, 1.3),
    return_prob=0.0,
    dispute_prob=0.0,
    return_delay_days=(1, 14),
    dispute_delay_days=(7, 60),
    primary_product_id: Optional[str] = None,
    primary_product_bias: float = 0.0,
    declined_frac: float = 0.0,
    business_hours_only: bool = False,
    late_night_bias: bool = False,
    dispute_reason_pool=None,
) -> pd.DataFrame:
    window_seconds = int((window_end - window_start).total_seconds())
    dispute_reason_pool = dispute_reason_pool or DISPUTE_REASONS_ABUSE
    cat_products = products[products["merchant_id"] == merchant_row.merchant_id]
    if cat_products.empty:
        return pd.DataFrame(columns=TXN_COLUMNS)

    rows = []
    for cust in customers.itertuples(index=False):
        n_orders = rng.integers(orders_per_customer[0], orders_per_customer[1] + 1)
        for _ in range(n_orders):
            if late_night_bias:
                day = rng.integers(0, max(window_seconds // 86400, 1))
                hour = rng.choice([0, 1, 2, 3, 4, 23], p=[0.2, 0.25, 0.25, 0.15, 0.1, 0.05])
                ts = window_start + timedelta(days=int(day), hours=int(hour), seconds=int(rng.integers(0, 3600)))
                ts = min(ts, window_end - timedelta(seconds=1))
            elif business_hours_only:
                offset = rng.integers(0, max(window_seconds, 1))
                ts = window_start + timedelta(seconds=int(offset))
                ts = ts.replace(hour=int(rng.integers(9, 18)), minute=int(rng.integers(0, 60)))
                ts = min(max(ts, window_start), window_end - timedelta(seconds=1))
            else:
                offset = rng.integers(0, max(window_seconds, 1))
                ts = window_start + timedelta(seconds=int(offset))

            if primary_product_id is not None and rng.random() < primary_product_bias:
                product_id = primary_product_id
                price = float(products.loc[products["product_id"] == primary_product_id, "price"].iloc[0])
            else:
                pick = cat_products.sample(n=1, random_state=int(rng.integers(0, 2**31 - 1))).iloc[0]
                product_id = pick["product_id"]
                price = float(pick["price"])

            amount = round(price * float(rng.uniform(*amount_multiplier)), 2)
            declined = rng.random() < declined_frac
            status = "declined" if declined else "approved"

            is_returned = (not declined) and rng.random() < return_prob
            is_disputed = (not declined) and (not is_returned) and rng.random() < dispute_prob
            if is_returned and rng.random() < 0.5:
                # some returned orders also end up disputed (refund never issued -> customer disputes)
                is_disputed = is_disputed or rng.random() < (dispute_prob * 0.5)

            returned_at = ts + timedelta(days=int(rng.integers(*return_delay_days))) if is_returned else None
            refunded_at = returned_at + timedelta(days=int(rng.integers(0, 3))) if is_returned else None
            disputed_at = ts + timedelta(days=int(rng.integers(*dispute_delay_days))) if is_disputed else None

            rows.append({
                "transaction_id": ids.next_transaction_id(),
                "merchant_id": merchant_row.merchant_id,
                "customer_id": cust.customer_id,
                "amount": amount,
                "timestamp": ts,
                "payment_method": cust.preferred_payment_method,
                "device_id": cust.home_device_id,
                "address_id": cust.home_address_id,
                "product_id": product_id,
                "status": status,
                "is_returned": bool(is_returned),
                "returned_at": returned_at,
                "is_refunded": bool(is_returned),
                "refunded_at": refunded_at,
                "is_disputed": bool(is_disputed),
                "disputed_at": disputed_at,
                "dispute_reason": rng.choice(dispute_reason_pool) if is_disputed else None,
                "is_fraud": is_fraud,
                "scenario_id": scenario_id,
                "scenario_type": scenario_type,
            })
    return pd.DataFrame(rows, columns=TXN_COLUMNS) if rows else pd.DataFrame(columns=TXN_COLUMNS)


def _select_and_flip(
    transactions: pd.DataFrame,
    merchant_id: str,
    rng: np.random.Generator,
    n: int,
    lookback_start: pd.Timestamp,
    lookback_end: pd.Timestamp,
    flip_to: str,  # "dispute" | "return"
    event_window_start: pd.Timestamp,
    event_window_end: pd.Timestamp,
    scenario_id: str,
    scenario_type: str,
    is_fraud: bool,
    dispute_reason_pool=None,
):
    dispute_reason_pool = dispute_reason_pool or DISPUTE_REASONS_ABUSE
    mask = (
        (transactions["merchant_id"] == merchant_id)
        & (transactions["timestamp"] >= lookback_start)
        & (transactions["timestamp"] < lookback_end)
        & (transactions["status"] == "approved")
    )
    if flip_to == "dispute":
        mask &= ~transactions["is_disputed"]
    else:
        mask &= ~transactions["is_returned"]

    candidates = transactions.index[mask]
    if len(candidates) == 0:
        return pd.Index([]), pd.DataFrame(columns=transactions.columns)

    n = min(n, len(candidates))
    chosen = rng.choice(candidates.to_numpy(), size=n, replace=False)
    window_seconds = int((event_window_end - event_window_start).total_seconds())

    updates = transactions.loc[chosen].copy()
    for idx in chosen:
        event_ts = event_window_start + timedelta(seconds=int(rng.integers(0, max(window_seconds, 1))))
        if flip_to == "dispute":
            updates.loc[idx, "is_disputed"] = True
            updates.loc[idx, "disputed_at"] = event_ts
            updates.loc[idx, "dispute_reason"] = rng.choice(dispute_reason_pool)
        else:
            updates.loc[idx, "is_returned"] = True
            updates.loc[idx, "returned_at"] = event_ts
            updates.loc[idx, "is_refunded"] = True
            updates.loc[idx, "refunded_at"] = event_ts + timedelta(days=int(rng.integers(0, 3)))
        updates.loc[idx, "is_fraud"] = is_fraud
        updates.loc[idx, "scenario_id"] = scenario_id
        updates.loc[idx, "scenario_type"] = scenario_type
    return pd.Index(chosen), updates


# ---------------------------------------------------------------------------
# Loss scenarios
# ---------------------------------------------------------------------------

def coordinated_return_ring(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    ring_size = params.get("ring_size", 20)
    n_shared_devices = params.get("shared_devices", 3)
    duration_hours = params.get("duration_hours", 48)
    return_probability = params.get("return_probability", 0.72)
    amount_mult = tuple(params.get("amount_multiplier", [1.3, 2.2]))

    window_start = ctx.random_start(rng, duration_hours)
    window_end = window_start + timedelta(hours=duration_hours)
    event_id = ctx.ids.next_event_id(window_start.year)

    shared_devices = [ctx.ids.next_device_id() for _ in range(n_shared_devices)]
    cohort = _spawn_cohort(
        ring_size, merchant.merchant_id, window_start, rng, ctx.ids,
        shared_devices=shared_devices, address_pool=ctx.address_pool, segment="fraud_ring",
    )
    cat_products = ctx.products[ctx.products["merchant_id"] == merchant.merchant_id]
    primary_product = cat_products.sample(n=1, random_state=int(rng.integers(0, 2**31 - 1))).iloc[0]["product_id"] if not cat_products.empty else None

    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "coordinated_return_ring", True,
        orders_per_customer=(1, 3), amount_multiplier=amount_mult,
        return_prob=return_probability, dispute_prob=return_probability * 0.35,
        return_delay_days=(1, 4), dispute_delay_days=(5, 20),
        primary_product_id=primary_product, primary_product_bias=0.65,
        dispute_reason_pool=DISPUTE_REASONS_ABUSE,
    )
    cohort["scenario_id"] = event_id

    exposure = float(txns.loc[txns["is_returned"] | txns["is_disputed"], "amount"].sum())
    manifest = ctx.manifest_entry(
        event_id, "coordinated_return_ring", "loss", merchant.merchant_id,
        window_start, window_end, txns, cohort, exposure, params,
        f"{ring_size} accounts across {n_shared_devices} shared devices returning/disputing "
        f"{primary_product or 'a concentrated SKU'} within {duration_hours}h.",
    )
    return cohort, txns, manifest


def sudden_fraud_spike(ctx, params, rng):
    affected_category = params.get("affected_category")
    candidates = ctx.merchants if not affected_category else ctx.merchants[ctx.merchants["category"] == affected_category]
    if candidates.empty:
        candidates = ctx.merchants
    merchant = candidates.sample(n=1, random_state=int(rng.integers(0, 2**31 - 1))).iloc[0]

    duration_hours = params.get("duration_hours", 6)
    baseline_rate = params.get("baseline_fraud_rate", 0.012)
    spike_rate = params.get("spike_rate", 0.085)
    est_daily_volume = params.get("estimated_daily_volume", 250)
    extra_count = max(40, int((spike_rate - baseline_rate) * est_daily_volume * (duration_hours / 24.0) * 10))

    window_start = ctx.random_start(rng, duration_hours)
    window_end = window_start + timedelta(hours=duration_hours)
    event_id = ctx.ids.next_event_id(window_start.year)

    cohort = _spawn_cohort(
        extra_count, merchant.merchant_id, window_start, rng, ctx.ids,
        address_pool=ctx.address_pool, device_pool=ctx.device_pool, segment="stolen_card",
    )
    cohort["preferred_payment_method"] = "card"

    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "fraud_spike", True,
        orders_per_customer=(1, 1), amount_multiplier=(1.5, 3.0),
        return_prob=0.0, dispute_prob=0.65,
        dispute_delay_days=(10, 40), declined_frac=0.35, late_night_bias=True,
        dispute_reason_pool=DISPUTE_REASONS_FRAUD,
    )
    cohort["scenario_id"] = event_id

    exposure = float(txns.loc[(txns["status"] == "approved"), "amount"].sum())
    manifest = ctx.manifest_entry(
        event_id, "fraud_spike", "loss", merchant.merchant_id,
        window_start, window_end, txns, cohort, exposure, params,
        f"Fraud rate spike ({baseline_rate:.1%} -> {spike_rate:.1%}) over {duration_hours}h, "
        f"card-testing pattern with {int(txns['status'].eq('declined').mean()*100) if len(txns) else 0}% declines.",
    )
    return cohort, txns, manifest


def chargeback_wave(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    n_transactions = params.get("n_transactions", 25)
    lookback_days = params.get("source_lookback_days", 35)
    duration_hours = params.get("duration_hours", 24)

    window_start = ctx.random_start(rng, duration_hours, min_lookback_days=lookback_days)
    window_end = window_start + timedelta(hours=duration_hours)
    lookback_start = window_start - timedelta(days=lookback_days)
    event_id = ctx.ids.next_event_id(window_start.year)

    idx, updated = _select_and_flip(
        ctx.baseline_transactions, merchant.merchant_id, rng, n_transactions,
        lookback_start, window_start, "dispute", window_start, window_end,
        event_id, "chargeback_wave", True, dispute_reason_pool=DISPUTE_REASONS_FRAUD,
    )
    exposure = float(updated["amount"].sum()) if len(updated) else 0.0
    manifest = ctx.manifest_entry(
        event_id, "chargeback_wave", "loss", merchant.merchant_id,
        window_start, window_end, updated, pd.DataFrame(), exposure, params,
        f"{len(updated)} transactions from the prior {lookback_days}d disputed within {duration_hours}h "
        f"(reason: {DISPUTE_REASONS_FRAUD}).",
    )
    return idx, updated, manifest


# ---------------------------------------------------------------------------
# Legitimate-but-unusual edge cases (section 34) -- must NOT be flagged as fraud
# ---------------------------------------------------------------------------

def false_positive_trap(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    n = params.get("legitimate_high_value_customers", 20)
    similarity = params.get("similarity_to_risky_cluster", "high")
    n_shared = 1 if similarity == "high" else 3

    window_start = ctx.random_start(rng, 24 * 14)
    window_end = window_start + timedelta(days=14)  # steady, not bursty
    event_id = ctx.ids.next_event_id(window_start.year)

    shared_devices = [ctx.ids.next_device_id() for _ in range(n_shared)]
    cohort = _spawn_cohort(
        n, merchant.merchant_id, window_start, rng, ctx.ids,
        shared_devices=shared_devices, address_pool=ctx.address_pool, segment="high_value",
    )
    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "false_positive_trap", False,
        orders_per_customer=(1, 3), amount_multiplier=(1.4, 2.5),
        return_prob=merchant.baseline_return_rate, dispute_prob=merchant.baseline_chargeback_rate,
        return_delay_days=(2, 12), dispute_delay_days=(10, 60),
    )
    cohort["scenario_id"] = event_id

    manifest = ctx.manifest_entry(
        event_id, "false_positive_trap", "edge_case", merchant.merchant_id,
        window_start, window_end, txns, cohort, 0.0, params,
        f"{n} high-value customers sharing {n_shared} device(s) (corporate procurement-like), "
        f"normal outcome rates spread over 14 days -- must NOT be flagged.",
    )
    return cohort, txns, manifest


def household_address_sharing(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    n = params.get("household_size", rng.integers(2, 5))
    window_start = ctx.random_start(rng, 24 * 30)
    window_end = window_start + timedelta(days=30)
    event_id = ctx.ids.next_event_id(window_start.year)

    shared_addr = [rng.choice(ctx.address_pool)]
    cohort = _spawn_cohort(
        n, merchant.merchant_id, window_start, rng, ctx.ids,
        shared_addresses=shared_addr, device_pool=ctx.device_pool, segment="household",
    )
    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "household_address_sharing", False,
        orders_per_customer=(1, 4), amount_multiplier=(0.7, 1.3),
        return_prob=merchant.baseline_return_rate, dispute_prob=merchant.baseline_chargeback_rate,
    )
    cohort["scenario_id"] = event_id
    manifest = ctx.manifest_entry(
        event_id, "household_address_sharing", "edge_case", merchant.merchant_id,
        window_start, window_end, txns, cohort, 0.0, params,
        f"{n} family members sharing one delivery address over 30 days, normal outcomes.",
    )
    return cohort, txns, manifest


def corporate_device_sharing(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    n = params.get("employee_count", 12)
    window_start = ctx.random_start(rng, 24 * 45)
    window_end = window_start + timedelta(days=45)
    event_id = ctx.ids.next_event_id(window_start.year)

    shared_devices = [ctx.ids.next_device_id(), ctx.ids.next_device_id()]
    cohort = _spawn_cohort(
        n, merchant.merchant_id, window_start, rng, ctx.ids,
        shared_devices=shared_devices, address_pool=ctx.address_pool, segment="corporate",
    )
    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "corporate_device_sharing", False,
        orders_per_customer=(1, 3), amount_multiplier=(1.0, 1.8),
        return_prob=merchant.baseline_return_rate * 0.5, dispute_prob=merchant.baseline_chargeback_rate * 0.3,
        business_hours_only=True,
    )
    cohort["scenario_id"] = event_id
    manifest = ctx.manifest_entry(
        event_id, "corporate_device_sharing", "edge_case", merchant.merchant_id,
        window_start, window_end, txns, cohort, 0.0, params,
        f"{n} employees ordering from 2 shared corporate devices, business hours only, low returns.",
    )
    return cohort, txns, manifest


def viral_product_spike(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    duration_hours = params.get("duration_hours", 30)
    n_customers = params.get("n_customers", 150)
    window_start = ctx.random_start(rng, duration_hours)
    window_end = window_start + timedelta(hours=duration_hours)
    event_id = ctx.ids.next_event_id(window_start.year)

    cat_products = ctx.products[ctx.products["merchant_id"] == merchant.merchant_id]
    if cat_products.empty:
        primary_product = None
    else:
        viral = cat_products[cat_products.get("is_viral_candidate", False) == True]
        pool = viral if not viral.empty else cat_products
        primary_product = pool.sample(n=1, random_state=int(rng.integers(0, 2**31 - 1))).iloc[0]["product_id"]

    cohort = _spawn_cohort(
        n_customers, merchant.merchant_id, window_start, rng, ctx.ids,
        device_pool=ctx.device_pool, address_pool=ctx.address_pool, segment="viral_buyer",
    )
    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "viral_product_spike", False,
        orders_per_customer=(1, 1), amount_multiplier=(0.9, 1.1),
        return_prob=merchant.baseline_return_rate, dispute_prob=merchant.baseline_chargeback_rate,
        primary_product_id=primary_product, primary_product_bias=0.95,
    )
    cohort["scenario_id"] = event_id
    manifest = ctx.manifest_entry(
        event_id, "viral_product_spike", "edge_case", merchant.merchant_id,
        window_start, window_end, txns, cohort, 0.0, params,
        f"{n_customers} unrelated new customers buying {primary_product or 'one SKU'} within {duration_hours}h "
        f"(no shared device/address), normal outcomes -- volume spike, not fraud.",
    )
    return cohort, txns, manifest


def new_customer_cold_start(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    n = params.get("n_customers", 30)
    window_start = ctx.random_start(rng, 24 * 10)
    window_end = window_start + timedelta(days=10)
    event_id = ctx.ids.next_event_id(window_start.year)

    cohort = _spawn_cohort(
        n, merchant.merchant_id, window_start, rng, ctx.ids,
        device_pool=ctx.device_pool, address_pool=ctx.address_pool, segment="new",
    )
    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "new_customer_cold_start", False,
        orders_per_customer=(1, 1), amount_multiplier=(0.8, 1.2),
        return_prob=merchant.baseline_return_rate, dispute_prob=merchant.baseline_chargeback_rate,
    )
    cohort["scenario_id"] = event_id
    manifest = ctx.manifest_entry(
        event_id, "new_customer_cold_start", "edge_case", merchant.merchant_id,
        window_start, window_end, txns, cohort, 0.0, params,
        f"{n} brand-new customers, single order each, no shared entities, normal outcomes.",
    )
    return cohort, txns, manifest


def promotional_campaign_spike(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    duration_hours = params.get("duration_hours", 24)
    n_customers = params.get("n_customers", 200)
    window_start = ctx.random_start(rng, duration_hours)
    window_end = window_start + timedelta(hours=duration_hours)
    event_id = ctx.ids.next_event_id(window_start.year)

    existing_pool = ctx.existing_customers[ctx.existing_customers["merchant_id"] == merchant.merchant_id]
    if len(existing_pool) == 0:
        return pd.DataFrame(), pd.DataFrame(columns=TXN_COLUMNS), None
    sample_n = min(n_customers, len(existing_pool))
    cohort = existing_pool.sample(n=sample_n, random_state=int(rng.integers(0, 2**31 - 1))).copy()

    txns = _burst_transactions(
        cohort, merchant, ctx.products, rng, ctx.ids,
        window_start, window_end, event_id, "promotional_campaign_spike", False,
        orders_per_customer=(1, 1), amount_multiplier=(0.6, 0.95),  # discounted
        return_prob=merchant.baseline_return_rate, dispute_prob=merchant.baseline_chargeback_rate,
    )
    manifest = ctx.manifest_entry(
        event_id, "promotional_campaign_spike", "edge_case", merchant.merchant_id,
        window_start, window_end, txns, pd.DataFrame(), 0.0, params,
        f"Broad {duration_hours}h promo: {sample_n} existing customers, discounted orders, normal outcomes "
        f"-- volume spike across the whole base, not concentrated.",
    )
    return pd.DataFrame(), txns, manifest


def seasonal_return_spike(ctx, params, rng):
    merchant = ctx.pick_merchant(rng)
    n_transactions = params.get("n_transactions", 60)
    lookback_days = params.get("source_lookback_days", 21)
    duration_hours = params.get("duration_hours", 72)

    window_start = ctx.random_start(rng, duration_hours, min_lookback_days=lookback_days)
    window_end = window_start + timedelta(hours=duration_hours)
    lookback_start = window_start - timedelta(days=lookback_days)
    event_id = ctx.ids.next_event_id(window_start.year)

    idx, updated = _select_and_flip(
        ctx.baseline_transactions, merchant.merchant_id, rng, n_transactions,
        lookback_start, window_start, "return", window_start, window_end,
        event_id, "seasonal_return_spike", False, dispute_reason_pool=DISPUTE_REASONS_ABUSE,
    )
    manifest = ctx.manifest_entry(
        event_id, "seasonal_return_spike", "edge_case", merchant.merchant_id,
        window_start, window_end, updated, pd.DataFrame(), 0.0, params,
        f"{len(updated)} broad-based returns across unrelated customers over {duration_hours}h "
        f"(e.g. post-holiday) -- elevated return rate, but no entity clustering.",
    )
    return idx, updated, manifest


SCENARIO_REGISTRY = {
    "coordinated_return_ring": coordinated_return_ring,
    "fraud_spike": sudden_fraud_spike,
    "chargeback_wave": chargeback_wave,
    "false_positive_trap": false_positive_trap,
    "household_address_sharing": household_address_sharing,
    "corporate_device_sharing": corporate_device_sharing,
    "viral_product_spike": viral_product_spike,
    "new_customer_cold_start": new_customer_cold_start,
    "promotional_campaign_spike": promotional_campaign_spike,
    "seasonal_return_spike": seasonal_return_spike,
}

MUTATING_SCENARIOS = {"chargeback_wave", "seasonal_return_spike"}
