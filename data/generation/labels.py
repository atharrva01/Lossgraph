"""
Splits the assembled transaction table into a feature table (what a model
may see) and a ground-truth label table (what only the evaluation harness
may see). Keeping these physically separate makes label leakage a code
smell instead of an easy mistake -- exactly what section 27's "never leak
future behavioural information into training" is guarding against.
"""

import numpy as np
import pandas as pd

LABEL_COLUMNS = ["is_fraud", "scenario_id", "scenario_type"]


def split_features_and_labels(transactions: pd.DataFrame):
    labels = transactions[["transaction_id"] + LABEL_COLUMNS].copy()
    labels["category"] = np.where(
        labels["scenario_type"] == "normal",
        "normal",
        np.where(labels["is_fraud"], "loss", "edge_case"),
    )
    features = transactions.drop(columns=LABEL_COLUMNS)
    return features, labels
