"""
CLI entrypoint: generates the full synthetic LossGraph dataset.

Usage:
    python -m data.generation.generate --scale demo --seed 42
    python -m data.generation.generate --scale full --out-dir data/output_full

Pipeline:
    entities -> baseline behaviour -> scenario injection (per split,
    additive + mutating) -> split assignment -> entity/relationship graph
    -> feature/label separation -> export
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # allow `python data/generation/generate.py`

from data.generation.config import DEFAULT_TIME_CONFIG, SCALES, TimeConfig
from data.generation.context import ScenarioContext
from data.generation.entities import (
    generate_addresses, generate_customers, generate_devices,
    generate_merchants, generate_products,
)
from data.generation.behavior import generate_baseline_transactions
from data.generation.scenarios import MUTATING_SCENARIOS, SCENARIO_REGISTRY, IdCounters, TXN_COLUMNS
from data.generation.relationships import build_entities, build_relationships
from data.generation.labels import split_features_and_labels
from data.generation.split import assign_split
from data.generation.export import export_dataset

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def load_scenario_configs() -> list:
    configs = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        with open(path) as f:
            configs.append(json.load(f))
    return configs


def run_scenarios(
    split: str,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    configs: list,
    merchants: pd.DataFrame,
    products: pd.DataFrame,
    device_pool: np.ndarray,
    address_pool: np.ndarray,
    existing_customers: pd.DataFrame,
    baseline_transactions: pd.DataFrame,
    ids: IdCounters,
    rng: np.random.Generator,
):
    ctx = ScenarioContext(
        merchants=merchants, products=products, device_pool=device_pool, address_pool=address_pool,
        existing_customers=existing_customers, baseline_transactions=baseline_transactions,
        ids=ids, window_start=window_start, window_end=window_end, split=split,
    )
    new_customers, new_transactions, manifest_entries = [], [], []

    for cfg in configs:
        scenario_type = cfg["scenario_type"]
        n_instances = cfg["instances"].get(split, 0)
        fn = SCENARIO_REGISTRY[scenario_type]
        for _ in range(n_instances):
            if scenario_type in MUTATING_SCENARIOS:
                idx, updated, manifest = fn(ctx, cfg["params"], rng)
                if manifest is not None and len(updated):
                    baseline_transactions.loc[idx, updated.columns] = updated
                    manifest_entries.append(manifest)
            else:
                cohort, txns, manifest = fn(ctx, cfg["params"], rng)
                if manifest is None:
                    continue
                if len(cohort):
                    new_customers.append(cohort)
                if len(txns):
                    new_transactions.append(txns)
                manifest_entries.append(manifest)

    return new_customers, new_transactions, manifest_entries


def generate(scale_name: str, seed: int, out_dir: str, time_config: TimeConfig) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)
    scale = SCALES[scale_name]

    print(f"[1/6] Generating baseline entities (scale={scale_name})...")
    merchants = generate_merchants(scale, rng)
    products = generate_products(scale, merchants, rng)
    devices = generate_devices(scale, time_config, rng)
    addresses = generate_addresses(scale, time_config, rng)
    customers = generate_customers(scale, merchants, devices, addresses, time_config, rng)

    print("[2/6] Generating baseline transaction behaviour...")
    baseline_transactions = generate_baseline_transactions(
        customers, products, merchants, devices, addresses, time_config, rng,
    )
    print(f"      {len(baseline_transactions):,} baseline transactions across {len(customers):,} customers")

    ids = IdCounters(customer=len(customers), transaction=len(baseline_transactions), device=0, event=0)
    device_pool = devices["device_id"].to_numpy()
    address_pool = addresses["address_id"].to_numpy()
    configs = load_scenario_configs()

    print(f"[3/6] Injecting {len(configs)} scenario types per split (train/val/test)...")
    all_new_customers, all_new_transactions, all_manifest = [], [], []
    for split in ["train", "val", "test"]:
        start, end = time_config.window_for_split(split)
        new_customers, new_transactions, manifest_entries = run_scenarios(
            split, pd.Timestamp(start), pd.Timestamp(end), configs,
            merchants, products, device_pool, address_pool,
            customers, baseline_transactions, ids, rng,
        )
        all_new_customers.extend(new_customers)
        all_new_transactions.extend(new_transactions)
        all_manifest.extend(manifest_entries)
        print(f"      {split}: {len(manifest_entries)} scenario instances injected")

    new_customer_frames = [df for df in all_new_customers if len(df)]
    all_customers = pd.concat([customers] + new_customer_frames, ignore_index=True) if new_customer_frames else customers

    new_txn_frames = [df for df in all_new_transactions if len(df)]
    all_transactions = pd.concat(
        [baseline_transactions] + new_txn_frames, ignore_index=True,
    ) if new_txn_frames else baseline_transactions
    all_transactions = all_transactions.sort_values("timestamp").reset_index(drop=True)
    all_transactions["split"] = assign_split(all_transactions["timestamp"], time_config)

    print("[4/6] Building entity/relationship graph...")
    entities = build_entities(all_transactions, all_customers)
    relationships = build_relationships(all_transactions)
    print(f"      {len(entities):,} entities, {len(relationships):,} relationships")

    print("[5/6] Splitting features from ground-truth labels...")
    features, labels = split_features_and_labels(all_transactions)

    print("[6/6] Exporting dataset...")
    summary = export_dataset(
        out_dir,
        merchants=merchants, customers=all_customers, devices=devices, addresses=addresses,
        products=products, transactions_features=features, labels=labels,
        entities=entities, relationships=relationships, scenario_manifest=all_manifest,
        time_config=time_config, scale_name=scale_name, seed=seed,
    )

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Output: {Path(out_dir).resolve()}")
    print(json.dumps(summary, indent=2, default=str))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Generate the LossGraph synthetic dataset")
    parser.add_argument("--scale", choices=["demo", "full"], default="demo")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parents[1] / "output"))
    parser.add_argument("--train-days", type=int, default=DEFAULT_TIME_CONFIG.train_days)
    parser.add_argument("--val-days", type=int, default=DEFAULT_TIME_CONFIG.val_days)
    parser.add_argument("--test-days", type=int, default=DEFAULT_TIME_CONFIG.test_days)
    args = parser.parse_args()

    time_config = TimeConfig(
        start_date=DEFAULT_TIME_CONFIG.start_date,
        train_days=args.train_days,
        val_days=args.val_days,
        test_days=args.test_days,
    )
    generate(args.scale, args.seed, args.out_dir, time_config)


if __name__ == "__main__":
    main()
