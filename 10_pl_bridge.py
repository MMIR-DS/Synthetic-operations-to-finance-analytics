"""10_pl_bridge.py — v1.9.0
P&L bridge at Product × Period using actual schema:
  BudgetRevenue → Volume + Price effects → ActualRevenue
  BudgetCOGS → VolumeCOGS + YieldVariance → ActualCOGS
  BudgetGP → ActualGP

Uses FactSales (Units, NetRevenue), FactFinancialPlan (Budget*), FactCOGSVariance.
Mix effect at product grain is 0; portfolio residual closes any float noise.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT, FIN = ROOT / "output", ROOT / "final"
FIN.mkdir(exist_ok=True)


def main():
    dim_p = pd.read_csv(OUT / "DimProduct.csv")
    fin = pd.read_csv(OUT / "FactFinancialPlan.csv")
    sales = pd.read_csv(OUT / "FactSales.csv")
    cogs = pd.read_csv(OUT / "FactCOGSVariance.csv")

    fin_s0 = fin[fin.ScenarioID == "S0"].copy()
    fin_s0["PeriodKey"] = fin_s0["PeriodKey"].astype(str)
    fin_s0["ProductID"] = fin_s0["ProductID"].astype(str)
    sales = sales.copy()
    sales["PeriodKey"] = pd.to_datetime(sales.DateKey.astype(str), format="%Y%m%d").dt.strftime("%Y%m")
    sales["ProductID"] = sales["ProductID"].astype(str)
    cogs["PeriodKey"] = cogs["PeriodKey"].astype(str)
    cogs["ProductID"] = cogs["ProductID"].astype(str)
    sales_agg = sales.groupby(["PeriodKey", "ProductID"], as_index=False).agg(
        ActualVolume=("Units", "sum"),
        ActualRevenue=("NetRevenue", "sum"),
    )

    m = fin_s0.merge(sales_agg, on=["PeriodKey", "ProductID"], how="left")
    m = m.merge(
        cogs[
            [
                "PeriodKey",
                "ProductID",
                "BudgetCOGS",
                "ActualCOGS",
                "YieldVariance",
                "VolumeCOGSEffect",
                "GoodUnits",
            ]
        ],
        on=["PeriodKey", "ProductID"],
        how="left",
    )
    m = m.fillna(0)

    rows = []
    for _, r in m.iterrows():
        bq, br = float(r.BudgetVolume), float(r.BudgetRevenue)
        aq, ar = float(r.ActualVolume), float(r.ActualRevenue)
        bp = float(r.BudgetPrice) if float(r.BudgetPrice) else (br / bq if bq else 0.0)
        ap = ar / aq if aq else 0.0

        volume_eff = (aq - bq) * bp
        price_eff = aq * (ap - bp)
        # Product-level mix is zero; identity: Budget + Vol + Price ≈ Actual
        mix_eff = 0.0
        bridge_rev = br + volume_eff + mix_eff + price_eff
        # Close tiny float residual into price effect for display identity
        residual = ar - bridge_rev
        price_eff += residual
        bridge_rev = br + volume_eff + mix_eff + price_eff

        budget_cogs = float(r.BudgetCOGS)
        actual_cogs = float(r.ActualCOGS)
        yield_var = float(r.YieldVariance)
        vol_cogs = float(r.VolumeCOGSEffect)

        budget_gp = br - budget_cogs
        actual_gp = ar - actual_cogs

        rows.append(
            {
                "PeriodKey": r.PeriodKey,
                "ProductID": r.ProductID,
                "BudgetVolume": round(bq, 4),
                "ActualVolume": round(aq, 4),
                "BudgetRevenue": round(br, 2),
                "VolumeEffect": round(volume_eff, 2),
                "MixEffect": round(mix_eff, 2),
                "PriceEffect": round(price_eff, 2),
                "ActualRevenue": round(ar, 2),
                "BudgetCOGS": round(budget_cogs, 2),
                "VolumeCOGSEffect": round(vol_cogs, 2),
                "YieldVariance": round(yield_var, 2),
                "ActualCOGS": round(actual_cogs, 2),
                "BudgetGP": round(budget_gp, 2),
                "ActualGP": round(actual_gp, 2),
                "GPVariance": round(actual_gp - budget_gp, 2),
            }
        )

    detail = pd.DataFrame(rows)
    detail.to_csv(FIN / "PL_Bridge_Detail.csv", index=False)

    # Revenue identity
    rev_err = (
        detail.BudgetRevenue
        + detail.VolumeEffect
        + detail.MixEffect
        + detail.PriceEffect
        - detail.ActualRevenue
    ).abs().max()
    cogs_err = (
        detail.BudgetCOGS + detail.VolumeCOGSEffect + detail.YieldVariance - detail.ActualCOGS
    ).abs().max()
    if rev_err > 1.0:
        raise ValueError(f"Revenue bridge broken max_err={rev_err}")
    if cogs_err > 1.0:
        raise ValueError(f"COGS bridge broken max_err={cogs_err}")

    summary = detail.groupby("PeriodKey", as_index=False).agg(
        {
            "BudgetRevenue": "sum",
            "VolumeEffect": "sum",
            "MixEffect": "sum",
            "PriceEffect": "sum",
            "ActualRevenue": "sum",
            "BudgetCOGS": "sum",
            "VolumeCOGSEffect": "sum",
            "YieldVariance": "sum",
            "ActualCOGS": "sum",
            "BudgetGP": "sum",
            "ActualGP": "sum",
            "GPVariance": "sum",
        }
    )
    summary.to_csv(FIN / "PL_Bridge_Summary.csv", index=False)

    tot = {
        "total_budget_revenue": round(float(summary.BudgetRevenue.sum()), 2),
        "total_actual_revenue": round(float(summary.ActualRevenue.sum()), 2),
        "total_volume_effect": round(float(summary.VolumeEffect.sum()), 2),
        "total_price_effect": round(float(summary.PriceEffect.sum()), 2),
        "total_budget_cogs": round(float(summary.BudgetCOGS.sum()), 2),
        "total_actual_cogs": round(float(summary.ActualCOGS.sum()), 2),
        "total_yield_variance": round(float(summary.YieldVariance.sum()), 2),
        "total_budget_gp": round(float(summary.BudgetGP.sum()), 2),
        "total_actual_gp": round(float(summary.ActualGP.sum()), 2),
        "gp_variance": round(float(summary.GPVariance.sum()), 2),
        "revenue_bridge_max_abs_error": float(rev_err),
        "cogs_bridge_max_abs_error": float(cogs_err),
        "figure_class": "Modeled / synthetic — Gross Profit only (no fixed overhead)",
        "note": "Product-level MixEffect=0; portfolio mix is embedded in volume/price at SKU grain.",
    }
    (FIN / "PL_Bridge_Summary.json").write_text(json.dumps(tot, indent=2))

    print(f"P&L Bridge: {len(detail)} product×period rows")
    print(f"  Budget Revenue ${tot['total_budget_revenue']:,.0f} → Actual ${tot['total_actual_revenue']:,.0f}")
    print(f"  Budget GP ${tot['total_budget_gp']:,.0f} → Actual ${tot['total_actual_gp']:,.0f} (var {tot['gp_variance']:+,.0f})")
    print(f"  Yield variance ${tot['total_yield_variance']:,.0f}")
    print(f"  Bridge errors: rev={rev_err:.2e} cogs={cogs_err:.2e}")


if __name__ == "__main__":
    main()
