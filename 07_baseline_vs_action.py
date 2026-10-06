"""Baseline vs Action comparison + risk-adjusted benefit (Decision Brief layer).

Baseline (A0): inventory absorption only — no OT recovery, no alternate-line substitution.
Action path:   engine waterfall (inventory + recovery + substitution) as in FactImpact.

Net operational benefit of Action vs Baseline ≈ NetCMOpportunity
  (Protected CM from recovery/substitution − recovery cost).

Risk-adjusted = max(0, Net operational) × P_REALIZE
  P_REALIZE from ModelAssumptions (default 0.65) — portfolio assumption, not estimated.

Outputs:
  final/Decision_Action_Comparison.csv
  final/Decision_Action_Summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
FIN = ROOT / "final"
OUT = ROOT / "output"


def load_p_realize() -> float:
    path = OUT / "ModelAssumptions.csv"
    if not path.exists():
        return 0.65
    ass = pd.read_csv(path)
    m = dict(zip(ass.Parameter.astype(str), ass.Value))
    if "P_REALIZE" not in m:
        return 0.65
    p = float(m["P_REALIZE"])
    if not (0.0 <= p <= 1.0):
        raise ValueError(f"P_REALIZE must be in [0,1], got {p}")
    return p


def main():
    impact_path = FIN / "FactImpact_ProductPeriod.csv"
    if not impact_path.exists():
        raise FileNotFoundError(f"Run engine first: missing {impact_path}")

    imp = pd.read_csv(impact_path)
    p_realize = load_p_realize()

    rows = []
    for _, r in imp.iterrows():
        gross = float(r.GrossGap)
        absorb = float(r.InventoryAbsorbed)
        gap_after_inv = max(0.0, gross - absorb)
        cm_u = float(r.CMUnit)
        price = float(r.ExpNetPrice)
        run_h = float(r.RunH) if float(r.RunH or 0) > 0 else 0.0
        good = float(r.GoodUnits or 0)
        primary_rate = (good / run_h) if run_h > 1e-9 else 0.0
        alt_rate = float(r.AltRate or 0)

        lost_b = gap_after_inv
        cm_exp_b = lost_b * cm_u
        protected_b = 0.0
        net_b = 0.0

        lost_a = float(r.PotentialLostSalesUnits)
        cm_exp_a = float(r.CMExposure)
        protected_a = float(r.ProtectedCM)
        rec_cost_a = float(r.RecoveryCost)
        net_a = float(r.NetCMOpportunity)
        recovered = float(r.RecoveredUnits)
        subst = float(r.SubstitutedUnits)

        delta_lost = lost_b - lost_a
        delta_cm_exp = cm_exp_b - cm_exp_a
        delta_net = net_a - net_b
        expected_net = max(0.0, delta_net) * p_realize

        if delta_net <= 0 and recovered + subst <= 0:
            action = "A0_do_nothing_or_accept"
        elif recovered + subst <= 0 and absorb > 0:
            action = "A1_buffer_only"
        elif subst > 0 and recovered > 0:
            action = "A2_A3_recover_and_divert"
        elif subst > 0:
            action = "A3_divert_alternate"
        elif recovered > 0:
            action = "A2_recover_primary"
        else:
            action = "A4_accept_shortfall"

        h_rec = (recovered / primary_rate) if primary_rate > 1e-9 and recovered > 0 else 0.0
        h_sub = (subst / alt_rate) if alt_rate > 1e-9 and subst > 0 else 0.0
        h_mit = h_rec + h_sub
        cm_per_h = (protected_a / h_mit) if h_mit > 1e-9 else float("nan")
        net_per_h = (net_a / h_mit) if h_mit > 1e-9 else float("nan")

        rows.append({
            "PeriodKey": r.PeriodKey,
            "ProductID": r.ProductID,
            "LineID": r.LineID,
            "GrossGap": round(gross, 4),
            "InventoryAbsorbed": round(absorb, 4),
            "Baseline_LostUnits": round(lost_b, 4),
            "Baseline_CMExposure": round(cm_exp_b, 2),
            "Action_RecoveredUnits": round(recovered, 4),
            "Action_SubstitutedUnits": round(subst, 4),
            "Action_LostUnits": round(lost_a, 4),
            "Action_CMExposure": round(cm_exp_a, 2),
            "Action_ProtectedCM": round(protected_a, 2),
            "Action_RecoveryCost": round(rec_cost_a, 2),
            "Action_NetCMOpportunity": round(net_a, 2),
            "Delta_LostUnits_Avoided": round(delta_lost, 4),
            "Delta_CMExposure_Avoided": round(delta_cm_exp, 2),
            "Delta_NetOperationalCM": round(delta_net, 2),
            "MitigationHours": round(h_mit, 4),
            "ProtectedCM_per_ConstrainedHour": round(cm_per_h, 2) if h_mit > 1e-9 else None,
            "NetCM_per_ConstrainedHour": round(net_per_h, 2) if h_mit > 1e-9 else None,
            "P_REALIZE": p_realize,
            "Expected_RiskAdjustedCM": round(expected_net, 2),
            "RecommendedAction": action,
        })

    out = pd.DataFrame(rows)
    out.to_csv(FIN / "Decision_Action_Comparison.csv", index=False)

    summary = {
        "definition_baseline": "Inventory absorption only; recovery_frac=0; no alternate-line substitution",
        "definition_action": "Engine waterfall: inventory + recovery + substitution (FactImpact)",
        "p_realize": p_realize,
        "p_realize_note": "Assumption from ModelAssumptions; not statistically estimated",
        "portfolio": {
            "baseline_cm_exposure": round(float(out.Baseline_CMExposure.sum()), 2),
            "action_cm_exposure": round(float(out.Action_CMExposure.sum()), 2),
            "delta_cm_exposure_avoided": round(float(out.Delta_CMExposure_Avoided.sum()), 2),
            "action_net_cm_opportunity": round(float(out.Action_NetCMOpportunity.sum()), 2),
            "delta_net_operational_cm": round(float(out.Delta_NetOperationalCM.sum()), 2),
            "expected_risk_adjusted_cm": round(float(out.Expected_RiskAdjustedCM.sum()), 2),
            "rows": int(len(out)),
            "rows_with_positive_delta_net": int((out.Delta_NetOperationalCM > 0).sum()),
        },
        "figure_class": "Modeled / assumption-driven / not a forecast",
        "ranking_note": (
            "Default rank: Expected_RiskAdjustedCM. "
            "Capacity-aware rank: NetCM_per_ConstrainedHour when MitigationHours > 0. "
            "CM/unit ranking can differ from CM/hour when rates differ across SKUs."
        ),
    }
    (FIN / "Decision_Action_Summary.json").write_text(json.dumps(summary, indent=2))

    print("Baseline vs Action summary:")
    print(json.dumps(summary["portfolio"], indent=2))
    print(f"P_REALIZE={p_realize}")
    print(f"Wrote {FIN / 'Decision_Action_Comparison.csv'}")
    print(f"Wrote {FIN / 'Decision_Action_Summary.json'}")


if __name__ == "__main__":
    main()
