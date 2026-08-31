"""Writes the generated dataset to disk as CSV + a JSON scenario manifest."""

import json
from pathlib import Path

import pandas as pd


def export_dataset(
    out_dir: str,
    *,
    merchants: pd.DataFrame,
    customers: pd.DataFrame,
    devices: pd.DataFrame,
    addresses: pd.DataFrame,
    products: pd.DataFrame,
    transactions_features: pd.DataFrame,
    labels: pd.DataFrame,
    entities: pd.DataFrame,
    relationships: pd.DataFrame,
    scenario_manifest: list,
    time_config,
    scale_name: str,
    seed: int,
) -> dict:
    out = Path(out_dir)
    (out / "ground_truth").mkdir(parents=True, exist_ok=True)

    merchants.to_csv(out / "merchants.csv", index=False)
    customers.to_csv(out / "customers.csv", index=False)
    devices.to_csv(out / "devices.csv", index=False)
    addresses.to_csv(out / "addresses.csv", index=False)
    products.to_csv(out / "products.csv", index=False)
    transactions_features.to_csv(out / "transactions.csv", index=False)
    entities.to_csv(out / "entities.csv", index=False)
    relationships.to_csv(out / "relationships.csv", index=False)

    labels.to_csv(out / "ground_truth" / "transaction_labels.csv", index=False)
    with open(out / "ground_truth" / "scenario_manifest.json", "w") as f:
        json.dump(scenario_manifest, f, indent=2, default=str)

    summary = {
        "scale": scale_name,
        "seed": seed,
        "time_window": {
            "start": str(time_config.start_date),
            "train_end": str(time_config.train_end),
            "val_end": str(time_config.val_end),
            "end": str(time_config.end_date),
        },
        "counts": {
            "merchants": len(merchants),
            "customers": len(customers),
            "devices": len(devices),
            "addresses": len(addresses),
            "products": len(products),
            "transactions": len(transactions_features),
            "entities": len(entities),
            "relationships": len(relationships),
            "scenarios_injected": len(scenario_manifest),
        },
        "split_counts": (
            transactions_features["split"].value_counts().to_dict()
            if "split" in transactions_features.columns else {}
        ),
        "label_counts": labels["category"].value_counts().to_dict(),
        "scenario_type_counts": (
            labels[labels["category"] != "normal"]["scenario_type"].value_counts().to_dict()
        ),
    }
    with open(out / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    return summary
