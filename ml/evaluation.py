"""Shared evaluation metrics: classification + economic (section 28)."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, f1_score, precision_recall_curve,
    precision_score, recall_score, roc_auc_score,
)


def classification_report(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    n_pos = int(y_true.sum())
    return {
        "threshold": round(float(threshold), 4),
        "n": int(len(y_true)),
        "n_positive": n_pos,
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4) if n_pos > 0 else None,
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if 0 < n_pos < len(y_true) else None,
        "flagged_rate": round(float(y_pred.mean()), 4),
    }


def best_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    f1 = np.where((precision + recall) > 0, 2 * precision * recall / (precision + recall + 1e-12), 0)
    if len(thresholds) == 0:
        return 0.5
    best_idx = int(np.argmax(f1[:-1])) if len(f1) > 1 else 0
    return float(thresholds[best_idx])


def best_economic_threshold(y_true: np.ndarray, y_prob: np.ndarray, amounts: np.ndarray,
                             false_positive_cost: float, verification_cost: float) -> float:
    """Scans candidate thresholds and returns the one maximizing net economic
    benefit (section 10-11) rather than F1 -- the objective the action
    optimizer actually cares about."""
    candidates = np.unique(np.quantile(y_prob, np.linspace(0, 1, 200)))
    best_threshold, best_benefit = 0.5, -np.inf
    for t in candidates:
        report = economic_report(y_true, y_prob, amounts, t, false_positive_cost, verification_cost)
        if report["net_benefit"] > best_benefit:
            best_benefit = report["net_benefit"]
            best_threshold = t
    return float(best_threshold)


def economic_report(y_true: np.ndarray, y_prob: np.ndarray, amounts: np.ndarray, threshold: float,
                     false_positive_cost: float, verification_cost: float) -> dict:
    """Section 28 economic metrics for a VERIFY-on-flag policy."""
    y_pred = (y_prob >= threshold).astype(int)
    tp = (y_pred == 1) & (y_true == 1)
    fp = (y_pred == 1) & (y_true == 0)
    fn = (y_pred == 0) & (y_true == 1)

    gross_loss = float(amounts[y_true == 1].sum())
    prevented_loss = float(amounts[tp].sum())
    missed_loss = float(amounts[fn].sum())
    fp_cost = float(fp.sum() * false_positive_cost)
    intervention_cost = float(y_pred.sum() * verification_cost)
    net_benefit = prevented_loss - fp_cost - intervention_cost

    return {
        "gross_loss": round(gross_loss, 2),
        "prevented_loss": round(prevented_loss, 2),
        "missed_loss": round(missed_loss, 2),
        "false_positive_count": int(fp.sum()),
        "false_positive_cost": round(fp_cost, 2),
        "intervention_count": int(y_pred.sum()),
        "intervention_cost": round(intervention_cost, 2),
        "net_benefit": round(net_benefit, 2),
        "loss_reduction_pct": round(100 * prevented_loss / gross_loss, 2) if gross_loss > 0 else None,
    }
