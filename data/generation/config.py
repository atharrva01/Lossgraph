"""
Configuration for the LossGraph synthetic data generator.

Two scales are provided:
- DEMO_SCALE: fast to generate (~seconds), enough volume/structure to exercise
  the graph engine, anomaly engine and evaluation harness end-to-end.
- FULL_SCALE: matches the PRD's suggested ecosystem size (section 32).
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ScaleConfig:
    n_merchants: int
    n_customers: int
    n_devices: int
    n_addresses: int
    n_products: int
    baseline_daily_transactions: int  # approx total baseline txns/day across all merchants


DEMO_SCALE = ScaleConfig(
    n_merchants=5,
    n_customers=2_000,
    n_devices=1_700,
    n_addresses=1_850,
    n_products=500,
    baseline_daily_transactions=350,
)

FULL_SCALE = ScaleConfig(
    n_merchants=50,
    n_customers=50_000,
    n_devices=42_000,
    n_addresses=46_000,
    n_products=10_000,
    baseline_daily_transactions=4_500,
)

SCALES = {"demo": DEMO_SCALE, "full": FULL_SCALE}


@dataclass(frozen=True)
class TimeConfig:
    start_date: date
    train_days: int
    val_days: int
    test_days: int

    @property
    def train_end(self) -> date:
        from datetime import timedelta

        return self.start_date + timedelta(days=self.train_days)

    @property
    def val_end(self) -> date:
        from datetime import timedelta

        return self.train_end + timedelta(days=self.val_days)

    @property
    def end_date(self) -> date:
        from datetime import timedelta

        return self.val_end + timedelta(days=self.test_days)

    @property
    def total_days(self) -> int:
        return self.train_days + self.val_days + self.test_days

    def window_for_split(self, split: str):
        """Return (start_date, end_date) for 'train' | 'val' | 'test'."""
        if split == "train":
            return self.start_date, self.train_end
        if split == "val":
            return self.train_end, self.val_end
        if split == "test":
            return self.val_end, self.end_date
        raise ValueError(f"Unknown split: {split}")


DEFAULT_TIME_CONFIG = TimeConfig(
    start_date=date(2026, 5, 1),
    train_days=60,
    val_days=15,
    test_days=25,
)


PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]

MERCHANT_CATEGORIES = ["electronics", "fashion", "grocery", "home_goods", "beauty"]

# Baseline (non-scenario) merchant loss priors, sampled around these means.
BASELINE_RETURN_RATE_RANGE = (0.015, 0.045)
BASELINE_REFUND_ONLY_RATE_RANGE = (0.005, 0.02)
BASELINE_CHARGEBACK_RATE_RANGE = (0.003, 0.012)
BASELINE_FRAUD_RATE_RANGE = (0.004, 0.018)
