"""Sensitivity of Net CM opportunity to RECOVERY_FRAC.

All cost parameters are loaded from output/ModelAssumptions.csv (required).
No silent financial hard-codes.

CMUnit must exist on FactImpact_ProductPeriod (written by the engine).
Missing CMUnit or non-finite values fail fast.

Outputs:
  final/Sensitivity_RecoveryFrac.csv
  final/Sensitivity_RecoveryFrac.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from shared.cost_model import mitigation_cost

ROOT = Path(__file__).resolve().parent
FIN = ROOT / "final"
OUT = ROOT / "output"

FRAC_GRID = [0.10, 0.20, 0.40]
REQUIRED_ASSUMPTIONS = ("RECOVERY_COST_UNIT",)


def load_assumptions(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Required assumptions file not found: {path}. "
            "Run 01_generate_synthetic_data_fixed.py first."
        )
    ass = pd.read_csv(path)
    if not {"Parameter", "Value"}.issubset(ass.columns):
        raise ValueError("ModelAssumptions.csv must have columns Parameter, Value")
    m = dict(zip(ass.Parameter.astype(str), ass.Value))
    missing = [k for k in REQUIRED_ASSUMPTIONS if k not in m]
    if missing:
        raise ValueError(f"Missing required assumptions: {missing}")

    cost = float(m["RECOVERY_COST_UNIT"])
    if cost < 0:
        raise ValueError(f"RECOVERY_COST_UNIT must be >= 0, got {cost}")

    if "RECOVERY_FRAC" in m:
        frac = float(m["RECOVERY_FRAC"])
        if not (0.0 <= frac <= 1.0):
            raise ValueError(f"RECOVERY_FRAC must be in [0,1], got {frac}")

    return {
        "RECOVERY_COST_UNIT": cost,
        "RECOVERY_FRAC_BASELINE": float(m["RECOVERY_FRAC"]) if "RECOVERY_FRAC" in m else None,
        "raw": m,
    }


def resolve_cm_unit(row: pd.Series) -> float:
    if "CMUnit" not in row.index or pd.isna(row["CMUnit"]):
        raise ValueError(
            f"CMUnit missing for PeriodKey={row.get('PeriodKey')} ProductID={row.get('ProductID')}. "
            "Re-run 02_oee_revenue_cm_engine_fixed.py so FactImpact includes CMUnit."
        )
    cm_u = float(row["CMUnit"])
    if not np.isfinite(cm_u):
        raise ValueError(
            f"Non-finite CMUnit for PeriodKey={row.get('PeriodKey')} ProductID={row.get('ProductID')}"
        )
    return cm_u


def main():
    impact_path = FIN / "FactImpact_ProductPeriod.csv"
    if not impact_path.exists():
        raise FileNotFoundError(f"Missing {impact_path}; run the engine first.")

    impact = pd.read_csv(impact_path)
    if "CMUnit" not in impact.columns:
        raise ValueError(
            "FactImpact_ProductPeriod.csv has no CMUnit column. "
            "Re-run 02_oee_revenue_cm_engine_fixed.py."
        )

    assumptions = load_assumptions(OUT / "ModelAssumptions.csv")
    recovery_cost_unit = assumptions["RECOVERY_COST_UNIT"]
    raw = assumptions.get("raw", {})
    mode = str(raw.get("RECOVERY_COST_MODE", "STEPPED")).upper()
    t1_f = float(raw.get("RECOVERY_TIER1_FRAC", 0.05))
    t1_c = float(raw.get("RECOVERY_TIER1_COST", 2.0))
    t2_f = float(raw.get("RECOVERY_TIER2_FRAC", 0.15))
    t2_c = float(raw.get("RECOVERY_TIER2_COST", 7.0))
    t3_c = float(raw.get("RECOVERY_TIER3_COST", 14.0))

    def _mc(units, gap_ref):
        return mitigation_cost(
            units, gap_ref,
            mode=mode,
            flat_unit_cost=recovery_cost_unit,
            tier1_frac=t1_f,
            tier1_cost=t1_c,
            tier2_frac=t2_f,
            tier2_cost=t2_c,
            tier3_cost=t3_c,
        )

    subst_cap = impact["SubstitutedUnits"].astype(float).clip(lower=0)
    rows = []

    for frac in FRAC_GRID:
        if not (0.0 <= frac <= 1.0):
            raise ValueError(f"Sensitivity grid frac out of range: {frac}")

        rec_list, subst_list, lost_list = [], [], []
        prot_list, cost_list, net_list = [], [], []

        for i, r in impact.iterrows():
            gross = float(r.GrossGap)
            absorb = float(r.InventoryAbsorbed)
            gap1 = max(0.0, gross - absorb)
            recovered = min(gap1, frac * gap1)
            gap2 = gap1 - recovered
            subst = min(gap2, float(subst_cap.loc[i]))
            lost = max(0.0, gap2 - subst)

            cm_u = resolve_cm_unit(r)
            protected = (recovered + subst) * cm_u
            cost = _mc(recovered + subst, gross if gross > 0 else recovered + subst)
            net = protected - cost

            rec_list.append(recovered)
            subst_list.append(subst)
            lost_list.append(lost)
            prot_list.append(protected)
            cost_list.append(cost)
            net_list.append(net)

        residual = (
            impact.GrossGap.values
            - impact.InventoryAbsorbed.values
            - np.array(rec_list)
            - np.array(subst_list)
            - np.array(lost_list)
        )
        max_res = float(np.max(np.abs(residual))) if len(residual) else 0.0
        if max_res > 1e-6:
            raise ValueError(f"Waterfall residual too large at frac={frac}: {max_res}")

        rows.append({
            "RecoveryFrac": frac,
            "Label": {0.10: "Conservative", 0.20: "Baseline", 0.40: "Optimistic"}[frac],
            "RecoveredUnits": round(float(np.sum(rec_list)), 2),
            "SubstitutedUnits": round(float(np.sum(subst_list)), 2),
            "LostSalesUnits": round(float(np.sum(lost_list)), 2),
            "ProtectedCM": round(float(np.sum(prot_list)), 2),
            "RecoveryCost": round(float(np.sum(cost_list)), 2),
            "NetCMOpportunity": round(float(np.sum(net_list)), 2),
            "WaterfallResidualMaxAbs": max_res,
            "FlatModeUnitCost": recovery_cost_unit,
            "Note": "Substitution capped at baseline demonstrated alternate-line volume",
        })

    df = pd.DataFrame(rows)
    df.to_csv(FIN / "Sensitivity_RecoveryFrac.csv", index=False)
    payload = {
        "description": "Sensitivity of mitigation economics to RECOVERY_FRAC",
        "assumption": "RECOVERY_FRAC is a modeling parameter, not an empirically fitted plant rate",
        "resolved_config": {
            "RECOVERY_COST_UNIT": recovery_cost_unit,
            "RECOVERY_FRAC_BASELINE": assumptions["RECOVERY_FRAC_BASELINE"],
            "source": str(OUT / "ModelAssumptions.csv"),
        },
        "results": rows,
    }
    json.dump(payload, open(FIN / "Sensitivity_RecoveryFrac.json", "w"), indent=2)
    print(df.to_string(index=False))
    print(f"\nResolved RECOVERY_COST_UNIT={recovery_cost_unit} from ModelAssumptions.csv")
    print(f"Wrote {FIN / 'Sensitivity_RecoveryFrac.csv'}")


if __name__ == "__main__":
    main()
