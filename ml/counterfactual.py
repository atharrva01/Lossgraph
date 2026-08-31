"""
Counterfactual Policy Simulator + Action Optimizer (PRD sections 9-11, 24).

For each Loss Event, simulates candidate interventions and recommends
whichever maximizes expected net economic benefit -- not whichever has the
best precision/recall, and not "block everything above a score." A
low-confidence event should get a light touch even if it's real; a
high-confidence event should get a firm one even if a few legitimate orders
are caught in it. The choice is driven by the merchant's own declared
false-positive cost and verification cost (section 25), not a hardcoded
threshold.

ACTION economics (prevention_rate, cost_per_txn, friction) are a
deliberately simple, documented starting model -- not fit to data. That's
consistent with the PRD's own framing: the interesting claim is that
*economically-driven* action selection beats *score-threshold* selection,
which doesn't require the economics themselves to be perfectly calibrated,
just directionally honest.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.fusion import build_fused_scores

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "output"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

# prevention_rate: fraction of a genuine loss stopped if this action is applied.
# cost_multiplier: operational cost per affected transaction, as a multiple
#   of the merchant's verification_cost.
# fp_cost_mode: how a legitimate order caught by this action actually costs
#   the merchant --
#     "none"      -- nothing happens to it (allow/monitor)
#     "flat"      -- the merchant's own false_positive_cost (friction/support
#                     overhead; the order still typically completes)
#     "flat_2x"   -- same, doubled (hold = longer delay = more annoyance)
#     "lost_sale" -- the FULL order amount, because the order never happens
#                     at all -- this is what makes blocking categorically
#                     different from verifying: a flat friction cost is the
#                     wrong model for "we refused a legitimate ₹8,000 order."
ACTIONS = {
    "allow":               {"prevention_rate": 0.00, "cost_multiplier": 0.0,  "fp_cost_mode": "none"},
    "monitor":              {"prevention_rate": 0.00, "cost_multiplier": 0.05, "fp_cost_mode": "none"},
    "verify":               {"prevention_rate": 0.80, "cost_multiplier": 1.0,  "fp_cost_mode": "flat"},
    "hold":                 {"prevention_rate": 0.92, "cost_multiplier": 2.5,  "fp_cost_mode": "flat_2x"},
    "block":                {"prevention_rate": 1.00, "cost_multiplier": 0.0,  "fp_cost_mode": "lost_sale"},
    "investigate_cluster":  {"prevention_rate": 0.80, "cost_multiplier": 1.0,  "fp_cost_mode": "flat"},  # verify-grade, core members only
}
CORE_MEMBER_THRESHOLD = 0.7  # investigate_cluster only intervenes on txns scoring at/above this


def simulate_policy(txn_scores: pd.DataFrame, action: str, merchant_row) -> dict:
    params = ACTIONS[action]
    scored = txn_scores.copy()

    if action == "investigate_cluster":
        scored = scored[scored["fused_score"] >= CORE_MEMBER_THRESHOLD]
    n_total = len(txn_scores)
    n_affected = len(scored)

    p = scored["fused_score"].to_numpy()
    amount = scored["amount"].to_numpy()

    loss_prevented = float((p * amount * params["prevention_rate"]).sum())
    residual_loss = float((p * amount * (1 - params["prevention_rate"])).sum())
    # Unaffected transactions (allow/monitor at threshold, or outside the
    # investigate_cluster subset) still carry their own expected loss --
    # nothing about them changed, so nothing was prevented.
    residual_loss += float((txn_scores.loc[~txn_scores.index.isin(scored.index), "fused_score"]
                             * txn_scores.loc[~txn_scores.index.isin(scored.index), "amount"]).sum())

    fp_cost_mode = params["fp_cost_mode"]
    legit_weight = (1 - p)  # expected count, per affected transaction, that is actually legitimate
    if fp_cost_mode == "none":
        expected_legit_orders_affected = 0.0
        false_positive_cost = 0.0
    elif fp_cost_mode == "flat":
        expected_legit_orders_affected = float(legit_weight.sum())
        false_positive_cost = expected_legit_orders_affected * float(merchant_row["false_positive_cost"])
    elif fp_cost_mode == "flat_2x":
        expected_legit_orders_affected = float(legit_weight.sum())
        false_positive_cost = expected_legit_orders_affected * float(merchant_row["false_positive_cost"]) * 2
    elif fp_cost_mode == "lost_sale":
        expected_legit_orders_affected = float(legit_weight.sum())
        false_positive_cost = float((legit_weight * (amount + float(merchant_row["false_positive_cost"]))).sum())
    else:
        raise ValueError(fp_cost_mode)

    operational_cost = n_affected * float(merchant_row["verification_cost"]) * params["cost_multiplier"]

    net_benefit = loss_prevented - false_positive_cost - operational_cost

    return {
        "action": action,
        "n_transactions_affected": n_affected,
        "n_transactions_total": n_total,
        "expected_loss_prevented": round(loss_prevented, 2),
        "expected_residual_loss": round(residual_loss, 2),
        "expected_legitimate_orders_affected": round(expected_legit_orders_affected, 2),
        "false_positive_cost": round(false_positive_cost, 2),
        "operational_cost": round(operational_cost, 2),
        "net_benefit": round(net_benefit, 2),
    }


def recommend_action(txn_scores: pd.DataFrame, merchant_row, event_source: str) -> dict:
    candidates = list(ACTIONS.keys())
    if event_source != "cluster":
        candidates = [a for a in candidates if a != "investigate_cluster"]  # only meaningful with a real cluster

    simulations = [simulate_policy(txn_scores, a, merchant_row) for a in candidates]
    best = max(simulations, key=lambda s: s["net_benefit"])
    return {"recommended_action": best["action"], "simulations": simulations}


def simulate_all_events() -> list:
    with open(ARTIFACT_DIR / "loss_events.json") as f:
        import json
        events = json.load(f)

    merchants = pd.read_csv(DATA_DIR / "merchants.csv").set_index("merchant_id")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    fused = build_fused_scores(transactions)[["transaction_id", "fused_score", "amount"]]

    for event in events:
        txn_scores = fused[fused["transaction_id"].isin(event["transaction_ids"])]
        merchant_row = merchants.loc[event["merchant_id"]]
        result = recommend_action(txn_scores, merchant_row, event["source"])
        event["counterfactual"] = result

    return events


if __name__ == "__main__":
    import json

    events = simulate_all_events()
    with open(ARTIFACT_DIR / "loss_events_with_policy.json", "w") as f:
        json.dump(events, f, indent=2, default=str)

    print(f"Simulated policies for {len(events)} events\n")
    pd.set_option("display.width", 200)

    rows = []
    for e in events:
        best = next(s for s in e["counterfactual"]["simulations"] if s["action"] == e["counterfactual"]["recommended_action"])
        allow = next(s for s in e["counterfactual"]["simulations"] if s["action"] == "allow")
        rows.append({
            "event_id": e["event_id"], "source": e["source"], "event_type": e["event_type"],
            "confidence": e["confidence"], "purity": e["ground_truth"]["purity"],
            "recommended_action": e["counterfactual"]["recommended_action"],
            "loss_prevented": best["expected_loss_prevented"],
            "legit_orders_affected": best["expected_legitimate_orders_affected"],
            "net_benefit": best["net_benefit"],
            "net_benefit_vs_allow": round(best["net_benefit"] - allow["net_benefit"], 2),
        })
    df = pd.DataFrame(rows).sort_values("net_benefit", ascending=False)
    print(df.to_string(index=False))

    print(f"\nAction distribution:\n{df['recommended_action'].value_counts()}")
    print(f"\nTotal net benefit vs. doing nothing (allow everywhere): "
          f"Rs {df['net_benefit_vs_allow'].sum():,.0f}")

    # Sanity check: does the optimizer's chosen aggressiveness track ground
    # truth? (It only sees confidence/economics, never the label itself.)
    action_rank = {"allow": 0, "monitor": 1, "investigate_cluster": 2, "verify": 3, "hold": 4, "block": 5}
    df["action_rank"] = df["recommended_action"].map(action_rank)
    print(f"\nMean action aggressiveness -- purity>=0.8 events: "
          f"{df.loc[df['purity']>=0.8,'action_rank'].mean():.2f}  |  "
          f"purity<0.2 events: {df.loc[df['purity']<0.2,'action_rank'].mean():.2f}")

    df.to_csv(ARTIFACT_DIR / "loss_events_policy_summary.csv", index=False)
