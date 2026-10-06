"""Build a compact executive/portfolio presentation pack from final outputs.

Creates:
- final/EXECUTIVE_CASE_STUDY.md
- final/charts/*.png
- final/Executive_KPIs.csv

No new analytical assumptions are introduced here; this is presentation-only.
"""
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIN = ROOT / "final"
CHARTS = FIN / "charts"
CHARTS.mkdir(exist_ok=True)

summary = json.loads((FIN / "Executive_Summary_Numbers.json").read_text())
decision = {}
if (FIN / "Decision_Action_Summary.json").exists():
    decision = json.loads((FIN / "Decision_Action_Summary.json").read_text())
dec_p = (decision.get("portfolio") or {})
p_real = decision.get("p_realize", 0.65)
pl = json.loads((FIN / "PL_Bridge_Summary.json").read_text()) if (FIN / "PL_Bridge_Summary.json").exists() else {}
br = json.loads((FIN / "Budget_CM_Gap_Reconciliation.json").read_text()) if (FIN / "Budget_CM_Gap_Reconciliation.json").exists() else {}
impact = pd.read_csv(FIN / "FactImpact_ProductPeriod.csv")
sens = pd.read_csv(FIN / "Sensitivity_RecoveryFrac.csv")
opp = pd.read_csv(FIN / "Opportunity_Prioritization.csv")

# 1) Financial bridge
labels = ["Residual CM\nexposure", "Protected CM\n(recovery + substitution)", "Recovery\ncost", "Net CM\nopportunity"]
values = [summary["cm_exposure"], summary["protected_cm"], summary["recovery_cost"], summary["net_cm_opportunity"]]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.bar(labels, values)
ax.set_title("OEE → Revenue → Contribution Margin: Financial Bridge")
ax.set_ylabel("USD")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(CHARTS / "01_financial_bridge.png", dpi=180)
plt.close(fig)

# 2) Unit waterfall
labels = ["Gross gap", "Inventory absorbed", "Recovered", "Substituted", "Potential lost sales"]
values = [
    impact.GrossGap.sum(),
    impact.InventoryAbsorbed.sum(),
    impact.RecoveredUnits.sum(),
    impact.SubstitutedUnits.sum(),
    impact.PotentialLostSalesUnits.sum(),
]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.bar(labels, values)
ax.set_title("Demand-Gap Waterfall")
ax.set_ylabel("EA")
ax.tick_params(axis="x", rotation=12)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(CHARTS / "02_unit_waterfall.png", dpi=180)
plt.close(fig)

# 3) Sensitivity
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(sens["RecoveryFrac"] * 100, sens["NetCMOpportunity"], marker="o")
ax.set_title("Recovery-Fraction Sensitivity")
ax.set_xlabel("Recovery fraction (%)")
ax.set_ylabel("Net CM opportunity (USD)")
ax.grid(True, alpha=0.25)
fig.tight_layout()
fig.savefig(CHARTS / "03_recovery_sensitivity.png", dpi=180)
plt.close(fig)

# 4) Top opportunities
rank = (opp.groupby("ProductID", as_index=False)
        .agg(CMExposure=("CMExposure", "sum"),
             NetCMOpportunity=("NetCMOpportunity", "sum"),
             LostSalesUnits=("PotentialLostSalesUnits", "sum"))
        .sort_values("NetCMOpportunity", ascending=False).head(8))
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.bar(rank["ProductID"], rank["NetCMOpportunity"])
ax.set_title("Product-Level Modeled Net CM Opportunity")
ax.set_ylabel("USD")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(CHARTS / "04_product_opportunity.png", dpi=180)
plt.close(fig)

kpis = pd.DataFrame([
    ["Time-weighted OEE", summary["oee_avg_time_weighted"], "%"],
    ["Actual net revenue", summary["total_revenue_actual"], "USD"],
    ["Actual contribution margin", summary["total_cm_actual"], "USD"],
    ["Gross production gap", summary["total_gross_gap_units"], "EA"],
    ["Opening inventory absorbed", summary["inventory_absorbed_units"], "EA"],
    ["Recovered units", summary["recovered_units"], "EA"],
    ["Substituted units", summary["substituted_units"], "EA"],
    ["Potential lost sales", summary["potential_lost_sales_units"], "EA"],
    ["Residual CM exposure", summary["cm_exposure"], "USD"],
    ["Protected CM", summary["protected_cm"], "USD"],
    ["Recovery cost", summary["recovery_cost"], "USD"],
    ["Modeled net CM opportunity", summary["net_cm_opportunity"], "USD"],
    ["Inventory holding cost", summary.get("inventory_holding_cost", 0), "USD"],
    ["Net CM after holding", summary.get("net_cm_after_holding", 0), "USD"],
], columns=["Metric", "Value", "Unit"])
kpis.to_csv(FIN / "Executive_KPIs.csv", index=False)

hold = float(summary.get("inventory_holding_cost") or 0)
net_h = float(summary.get("net_cm_after_holding") or (summary["net_cm_opportunity"] - hold))
budget_cm = float(summary.get("budget_cm") or 0)
cm_miss = budget_cm - float(summary["total_cm_actual"])

md = f'''# Executive Case Study — OEE → Revenue → Contribution Margin

**Portfolio version: 1.9.0** · Modeled / synthetic · not a forecast

## So what (read this first)

| Story layer | Number | Meaning |
|-------------|-------:|---------|
| Residual CM **exposure** | **${summary['cm_exposure']/1e6:.2f}M** | Margin on units still expected lost after mitigation path |
| Modeled **net CM opportunity** | **${summary['net_cm_opportunity']/1e6:.2f}M** | Protected CM − stepped recovery cost |
| Inventory **holding cost** | **${hold/1e6:.2f}M** | Avg FG × VC × (WACC/12); total FG not only OEE buffer |
| **Net CM after holding** | **${net_h/1e6:.2f}M** | Opportunity left after capital/storage proxy |

**Primary insight:** the modeled economics are highly sensitive to how inventory carrying cost is treated
(${summary['net_cm_opportunity']/1e6:.2f}M → ${net_h/1e6:.2f}M). In this synthetic case, **inventory policy can matter as much as OEE recovery**—especially under a total-FG holding proxy.

**Budget context:** actual CM **${summary['total_cm_actual']/1e6:.2f}M** vs budget **${budget_cm/1e6:.2f}M** → about **${cm_miss/1e6:.1f}M** CM shortfall vs plan. Residual CM exposure is a **partial** explanation of that miss (see also PVM).

**Critical assumption:** `RECOVERY_FRAC = {summary.get('recovery_frac_assumption', 0.2)}` is a modeling input, not a fitted plant probability.
With real data: estimate by loss category from downtime→shipment lags (or survival on recovery windows); do not use one global rate forever.

**Figure class:** all $ figures below are **Modeled / assumption-driven / scenario-dependent — not a forecast and not realized benefit.**

**Holding cost — three interpretations:**
| View | Approx. | Use |
|------|--------:|-----|
| No holding | **${summary['net_cm_opportunity']/1e6:.2f}M** | Mitigation value only |
| After incremental holding (**attributed proxy**) | **${float(summary.get("net_cm_after_incremental_holding") or summary["net_cm_opportunity"])/1e6:.2f}M** (incr. cost ~${float(summary.get("incremental_holding_cost") or 0)/1e6:.2f}M) | Not a full inventory counterfactual |
| After total FG holding | **${net_h/1e6:.2f}M** | Full carrying cost (can over-penalize recovery) |

## Budget CM shortfall vs OEE-path exposure

| Item | Modeled |
|------|--------:|
| Budget CM shortfall (plan − actual) | **${(br.get("cm_shortfall_vs_budget") or cm_miss)/1e6:.2f}M** |
| Residual CM exposure (after mitigation waterfall) | **${(br.get("oee_path_residual_cm_exposure") or summary["cm_exposure"])/1e6:.2f}M** |
| Residual CM exposure as share of budget-to-actual CM gap *(not causal attribution)* | **{100*float(br.get("share_of_shortfall_explained_by_residual_exposure") or (summary["cm_exposure"]/cm_miss if cm_miss else 0)):.1f}%** |
| Remainder (other drivers — not claimed as OEE opportunity) | **${(br.get("unexplained_or_other_drivers_approx") or (cm_miss-summary["cm_exposure"]))/1e6:.2f}M** |

Do **not** equate the budget miss with OEE opportunity. Detail: `final/Budget_CM_Gap_Reconciliation.md`.

### CM vs modeled Gross Profit (v1.9 — do not interchange)

| View | Definition | Current |
|------|------------|--------:|
| **Contribution margin** | Net revenue − standard variable cost (managerial) | Actual CM **${summary["total_cm_actual"]/1e6:.2f}M** |
| **Modeled GP** | Revenue − modeled COGS (std VC + yield variance) | Actual GP **${float(pl.get("total_actual_gp") or 0)/1e6:.2f}M** |

OEE mitigation economics use **CM**. The P&L bridge uses **modeled GP**. Different cost bases.

### Modeled standard-cost P&L bridge (v1.9)

| Item | Amount |
|------|-------:|
| Budget → Actual revenue | **${float(pl.get("total_budget_revenue") or 0)/1e6:.2f}M** → **${float(pl.get("total_actual_revenue") or 0)/1e6:.2f}M** |
| Volume / Price effects | **${float(pl.get("total_volume_effect") or 0)/1e6:.2f}M** / **${float(pl.get("total_price_effect") or 0)/1e6:.2f}M** |
| Yield variance | **${float(pl.get("total_yield_variance") or 0)/1e6:.2f}M** |
| Budget GP → Actual GP | **${float(pl.get("total_budget_gp") or 0)/1e6:.2f}M** → **${float(pl.get("total_actual_gp") or 0)/1e6:.2f}M** (var **${float(pl.get("gp_variance") or 0)/1e6:.2f}M**) |

Product-level MixEffect = 0 (SKU grain). No fixed overhead / EBITDA.

### P_REALIZE sensitivity (on net operational CM ${summary["net_cm_opportunity"]/1e6:.2f}M)

| P | Expected risk-adjusted |
|--:|-----------------------:|
| 0.40 | **${summary["net_cm_opportunity"]*0.40/1e6:.2f}M** |
| **{p_real:.2f} (baseline)** | **${float(dec_p.get("expected_risk_adjusted_cm") or summary["net_cm_opportunity"]*p_real)/1e6:.2f}M** |
| 0.85 | **${summary["net_cm_opportunity"]*0.85/1e6:.2f}M** |
| 1.00 | **${summary["net_cm_opportunity"]/1e6:.2f}M** |

`P_REALIZE` is an **assumption-based realization factor**, not a fitted probability. Table: `final/Sensitivity_P_Realize.csv`.

## Baseline vs Action (decision economics)

| View | Modeled $ | Meaning |
|------|----------:|---------|
| Baseline CM exposure (inventory only) | **${dec_p.get("baseline_cm_exposure", 0)/1e6:.2f}M** | If no OT recovery / divert |
| Action CM exposure | **${dec_p.get("action_cm_exposure", 0)/1e6:.2f}M** | After recovery + substitution |
| Exposure avoided by action | **${dec_p.get("delta_cm_exposure_avoided", 0)/1e6:.2f}M** | Baseline − action exposure |
| Net operational CM (action) | **${dec_p.get("delta_net_operational_cm", 0)/1e6:.2f}M** | Protected CM − recovery cost |
| Risk-adjusted (× P_REALIZE={p_real}) | **${dec_p.get("expected_risk_adjusted_cm", 0)/1e6:.2f}M** | Assumption, not fitted |

SKU–period detail: `final/Decision_Action_Comparison.csv`. Positive Δ net on **{dec_p.get("rows_with_positive_delta_net", "—")}** of **{dec_p.get("rows", "—")}** product-periods.

**2-minute verbal arc:** problem (OEE% ≠ $) → key number (**${net_h/1e6:.2f}M after total holding**) → assumption (recovery frac) → with real data, fit recovery empirically; do not present as guaranteed P&L benefit.


---

## Decision question
**When does an operational loss actually become a financial loss?**

This synthetic case study is set in an **imaginary dairy factory** (fillers, cold stores, CIP). It connects manufacturing performance to financial exposure without multiplying OEE by revenue. Recovery = overtime / alternate filler — not rework of spoiled milk.

## Baseline snapshot

| KPI | Result |
|---|---:|
| Time-weighted OEE | **{summary['oee_avg_time_weighted']:.2%}** |
| Actual net revenue | **${summary['total_revenue_actual']/1e6:.2f}M** |
| Actual contribution margin | **${summary['total_cm_actual']/1e6:.2f}M** |
| Gross production gap | **{summary['total_gross_gap_units']:,} EA** |
| Opening inventory absorbed | **{summary['inventory_absorbed_units']:,} EA** |
| Recovered units | **{summary['recovered_units']:,} EA** |
| Substituted units | **{summary['substituted_units']:,} EA** |
| Potential lost sales | **{summary['potential_lost_sales_units']:,} EA** |
| Residual CM exposure | **${summary['cm_exposure']/1e6:.2f}M** |
| Protected CM | **${summary['protected_cm']/1e6:.2f}M** |
| Recovery cost | **${summary['recovery_cost']/1e6:.2f}M** |
| Modeled net CM opportunity | **${summary['net_cm_opportunity']/1e6:.2f}M** |
| Inventory holding cost | **${hold/1e6:.2f}M** |
| **Net CM after holding** | **${net_h/1e6:.2f}M** |

## Analytical chain

```text
OEE (Availability × Performance × Quality)
        ↓
Good production / production gap
        ↓
Opening inventory absorption
        ↓
Recovery + valid alternate-line substitution
        ↓
Residual potential lost sales
        ↓
Revenue exposure + contribution-margin exposure
        ↓
Modeled mitigation value after recovery cost
```

## Critical modeling distinction

**Modeled net CM opportunity is not CM exposure minus recovery cost.**

It is:

`Protected CM from recovered/substituted units − recovery cost`

CM exposure refers only to the margin attached to **residual units still expected to be lost** after the modeled mitigation waterfall.

## What the model does not claim

- The data is synthetic and is not evidence about a real plant.
- Recovery fraction is an explicit modeling assumption, not a fitted operational probability.
- Same-period shipment is assumed; lead time and backlog carry-over are outside scope.
- Contribution margin excludes fixed manufacturing overhead, depreciation, allocated SG&A, and financing costs.
- No claim is made that every modeled opportunity is operationally or commercially realizable.
- Scenario outputs are directional analytical scenarios, not forecasts.

## Controls

The pipeline includes explicit tests for inventory roll-forward, demand-gap reconciliation, distinct alternate-line capability, exact sales-to-shipment reconciliation, CM identity, PVM reconciliation, domain constraints, nonfinite values, and scenario-parameter coverage.

## Scenario framing (directional)

| Label | Example scenarios | Intent |
|-------|-------------------|--------|
| **Base** | Engine baseline Impact | Current synthetic ops point (20% recovery, same-period ship) |
| **Optimistic** | e.g. S5 OEE +5pt; higher recovery mult. | Reliability / recovery capacity improve → more gap closed |
| **Stressed** | e.g. SDP demand +10% | Demand outruns primary + mitigation → exposure rises without OEE change |

`NetCMImpact_after_RecoveryCost` on scenarios is not the same identity as baseline `NetCMOpportunity`.

## Portfolio positioning

This project demonstrates a **manufacturing analytics → FP&A bridge** rather than an OEE dashboard. The emphasis is on traceability from operational loss to economically relevant exposure and mitigation value.
'''
(FIN / "EXECUTIVE_CASE_STUDY.md").write_text(md)
print("Executive pack created:", FIN / "EXECUTIVE_CASE_STUDY.md")

# ---------- execution_report.txt (v1.4: generated from final/ artifacts, not hand-maintained) ----------
# Rebuilt from the same run's own output files (integrity_checks.json,
# Executive_Summary_Numbers.json, Sensitivity_RecoveryFrac.csv) every time this script runs,
# so it can never drift out of sync with the numbers it reports, unlike the static v1.3 file
# it replaces.
from datetime import datetime, timezone

integrity = json.loads((FIN / "integrity_checks.json").read_text())
n_checks = len(integrity["checks"])
n_passed = sum(1 for c in integrity["checks"] if c["passed"])
sens_rows = sens.sort_values("RecoveryFrac")
sens_line = ", ".join(
    f"{int(row.RecoveryFrac*100)}%→${row.NetCMOpportunity:,.0f}" for _, row in sens_rows.iterrows()
)

report = f"""========================================================================
PIPELINE EXECUTION REPORT (auto-generated by 04_build_executive_pack.py)
Timestamp UTC: {datetime.now(timezone.utc).isoformat()}
Source run_id: {summary['run_id']}  (script_version {summary['script_version']})
========================================================================

Integrity overall: {"PASSED" if integrity["passed"] else "FAILED"} ({n_passed}/{n_checks} checks)
Fixture tests: run separately via tests/test_fixture_two_period.py (not re-executed here)

Key results (this run):
  Time-weighted OEE:            {summary['oee_avg_time_weighted']:.2%}
  Actual net revenue:           ${summary['total_revenue_actual']:,.2f}
  Actual contribution margin:   ${summary['total_cm_actual']:,.2f}
  Gross production gap:         {summary['total_gross_gap_units']:,} EA
  Opening inventory absorbed:   {summary['inventory_absorbed_units']:,} EA
  Recovered units:              {summary['recovered_units']:,} EA
  Substituted units:            {summary['substituted_units']:,} EA
  Potential lost sales:         {summary['potential_lost_sales_units']:,} EA
  CM exposure:                  ${summary['cm_exposure']:,.2f}
  Protected CM:                 ${summary['protected_cm']:,.2f}
  Recovery cost:                ${summary['recovery_cost']:,.2f}
  Net CM opportunity:           ${summary['net_cm_opportunity']:,.2f}

Recovery-fraction sensitivity (NetCMOpportunity): {sens_line}

Note: this file is regenerated from final/integrity_checks.json,
final/Executive_Summary_Numbers.json, and final/Sensitivity_RecoveryFrac.csv on every run
of 04_build_executive_pack.py. Do not hand-edit; re-run the pipeline instead.
========================================================================
"""
(ROOT / "execution_report.txt").write_text(report)
print("Execution report refreshed:", ROOT / "execution_report.txt")
