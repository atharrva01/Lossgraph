"""Chronological train/val/test split assignment."""

import numpy as np
import pandas as pd


def assign_split(timestamps: pd.Series, time_config) -> np.ndarray:
    train_end = pd.Timestamp(time_config.train_end)
    val_end = pd.Timestamp(time_config.val_end)
    conditions = [timestamps < train_end, timestamps < val_end]
    choices = ["train", "val"]
    return np.select(conditions, choices, default="test")
