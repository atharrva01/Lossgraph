"""
Engine 1 -- Transaction Risk Model.

Trains a LightGBM classifier on chronologically-split data (train -> fit,
val -> early stopping + threshold tuning, test -> held-out report). Only
pre-authorization features are used (see features.py); the fraud label
never leaks into X.
"""

import json
import sys
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.evaluation import best_economic_threshold, best_f1_threshold, classification_report, economic_report
from ml.features import CATEGORICAL_COLUMNS, FEATURE_COLUMNS, build_features

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


def load_dataset():
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    merchants = pd.read_csv(DATA_DIR / "merchants.csv")
    labels = pd.read_csv(DATA_DIR / "ground_truth" / "transaction_labels.csv")
    return transactions, customers, merchants, labels


def _split_xy(df: pd.DataFrame, split: str):
    sub = df[df["split"] == split]
    return sub[FEATURE_COLUMNS], sub["is_fraud"].astype(int), sub["amount"].to_numpy()


def train_and_evaluate(save_artifacts: bool = True) -> dict:
    transactions, customers, merchants, labels = load_dataset()
    features = build_features(transactions, customers, merchants)
    df = features.merge(labels[["transaction_id", "is_fraud"]], on="transaction_id")

    X_train, y_train, _ = _split_xy(df, "train")
    X_val, y_val, amt_val = _split_xy(df, "val")
    X_test, y_test, amt_test = _split_xy(df, "test")

    n_pos, n_neg = int(y_train.sum()), int((1 - y_train).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)
    print(f"Train: {len(X_train):,} rows, {n_pos:,} positive ({100*n_pos/len(X_train):.2f}%), scale_pos_weight={scale_pos_weight:.1f}")

    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=600,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbose=-1,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_metric="average_precision",
            categorical_feature=CATEGORICAL_COLUMNS,
            callbacks=[lgb.early_stopping(50, first_metric_only=True, verbose=False), lgb.log_evaluation(0)],
        )

    val_prob = model.predict_proba(X_val)[:, 1]
    test_prob = model.predict_proba(X_test)[:, 1]

    avg_fp_cost = float(merchants["false_positive_cost"].mean())
    avg_verification_cost = float(merchants["verification_cost"].mean())

    f1_threshold = best_f1_threshold(y_val.to_numpy(), val_prob)
    econ_threshold = best_economic_threshold(
        y_val.to_numpy(), val_prob, amt_val, avg_fp_cost, avg_verification_cost,
    )

    report = {
        "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        "n_train_positive": n_pos,
        "best_iteration": int(model.best_iteration_) if model.best_iteration_ else model.n_estimators,
        "val_default_0.5": classification_report(y_val.to_numpy(), val_prob, 0.5),
        "val_f1_tuned": classification_report(y_val.to_numpy(), val_prob, f1_threshold),
        "test_default_0.5": classification_report(y_test.to_numpy(), test_prob, 0.5),
        "test_f1_tuned_threshold": classification_report(y_test.to_numpy(), test_prob, f1_threshold),
        "test_econ_tuned_threshold": classification_report(y_test.to_numpy(), test_prob, econ_threshold),
        "f1_threshold": round(float(f1_threshold), 4),
        "econ_threshold": round(float(econ_threshold), 4),
    }

    # Two thresholds, chosen against two different objectives (both tuned on
    # val only, applied to test only). F1 is the usual ML-quality yardstick;
    # net economic benefit is what section 10-11 says the system should
    # actually optimize -- they don't have to agree, and honestly reporting
    # both is more useful than picking whichever looks better.
    report["test_economic_at_0.5"] = economic_report(
        y_test.to_numpy(), test_prob, amt_test, 0.5, avg_fp_cost, avg_verification_cost,
    )
    report["test_economic_at_f1_threshold"] = economic_report(
        y_test.to_numpy(), test_prob, amt_test, f1_threshold, avg_fp_cost, avg_verification_cost,
    )
    report["test_economic_at_econ_threshold"] = economic_report(
        y_test.to_numpy(), test_prob, amt_test, econ_threshold, avg_fp_cost, avg_verification_cost,
    )
    report["_economic_assumptions"] = {
        "avg_false_positive_cost": round(avg_fp_cost, 2),
        "avg_verification_cost": round(avg_verification_cost, 2),
        "note": "uniform merchant-averaged costs -- per-merchant policy optimization is the action optimizer (day 3).",
    }

    importance = pd.Series(model.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
    report["feature_importance_gain"] = importance.round(1).to_dict()

    try:
        import shap
        sample = X_test.sample(min(1500, len(X_test)), random_state=42)
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(sample)
        sv = sv[1] if isinstance(sv, list) else sv
        mean_abs_shap = pd.Series(np.abs(sv).mean(axis=0), index=FEATURE_COLUMNS).sort_values(ascending=False)
        report["shap_mean_abs"] = mean_abs_shap.round(4).to_dict()
    except Exception as e:  # noqa: BLE001 -- explainability is best-effort, never blocks scoring
        report["shap_mean_abs"] = None
        report["shap_error"] = f"{type(e).__name__}: {e}"

    if save_artifacts:
        ARTIFACT_DIR.mkdir(exist_ok=True)
        joblib.dump(model, ARTIFACT_DIR / "risk_model.joblib")
        with open(ARTIFACT_DIR / "risk_model_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        test_scores = df[df["split"] == "test"][["transaction_id"]].copy()
        test_scores["risk_score"] = test_prob
        test_scores.to_csv(ARTIFACT_DIR / "test_risk_scores.csv", index=False)

    return report


if __name__ == "__main__":
    report = train_and_evaluate()
    print(json.dumps(report, indent=2, default=str))
