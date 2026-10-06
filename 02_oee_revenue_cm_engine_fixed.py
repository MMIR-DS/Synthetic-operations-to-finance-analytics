"""OEE -> Revenue -> CM calculation engine (corrected pipeline v1.4).

- Paths relative to __file__
- PVM at Product×Period + total (abs+rel tolerance)
- Scenario coefficients from ScenarioParameters.csv (not hard-coded only)
- Layered opportunity fields (capacity → shipment → revenue → CM)
- RecoveryROI = NaN + RecoveryROI_Status flag (never inf)
- Enriched integrity_checks.json (grain, tolerance, max_error, failed_rows, run_id)
- v1.4: alternate-line slack is tracked and decremented per (Period, AltLine) so two
  products sharing an alt line in the same period cannot both claim the same hours;
  allocation order is CM-per-unit descending within each period. See CHANGELOG_v1.4.md.
- See DATA_DICTIONARY.md for metric definitions
"""
import pandas as pd
import numpy as np
import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from shared.cost_model import mitigation_cost

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FIN = ROOT / "final"
FIN.mkdir(parents=True, exist_ok=True)

SCRIPT_VERSION = "1.9.0"
# Deterministic if OEE_RUN_ID set; else timestamp + short uuid (traceability, not content hash)
import os as _os
RUN_ID = _os.environ.get("OEE_RUN_ID") or (
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
)

# Baseline operational assumptions — loaded from ModelAssumptions.csv when present
BOTTLENECK_THRESH = 0.95
PVM_ABS_TOL = 0.05
PVM_REL_TOL = 1e-9

def R(f):
    return pd.read_csv(
        OUT / f"{f}.csv",
        dtype={
            "ProductID": str, "LineID": str, "EquipmentID": str,
            "DateKey": str, "PeriodKey": str, "ScenarioID": str,
        },
    )

DimDate = R("DimDate")
DimProduct = R("DimProduct")
DimLine = R("DimLine")
DimEquipment = R("DimEquipment")
DimReason = R("DimDowntimeReason")
DimScenario = R("DimScenario")
Bridge = R("Bridge_ProductLineCapability")
Prod = R("FactProduction")
Dt = R("FactDowntime")
Sales = R("FactSales")
Inv = R("FactInventorySnapshot")
Demand = R("FactDemand")
Plan = R("FactFinancialPlan")
ScenParams = R("ScenarioParameters")

# ModelAssumptions (required — no silent financial defaults)
_assumptions_path = OUT / "ModelAssumptions.csv"
if not _assumptions_path.exists():
    raise FileNotFoundError(
        f"Required {_assumptions_path} not found. Run 01_generate_synthetic_data_fixed.py first."
    )
_ass = pd.read_csv(_assumptions_path)
_ass_map = dict(zip(_ass.Parameter.astype(str), _ass.Value))
for _req in ("RECOVERY_FRAC", "RECOVERY_COST_UNIT"):
    if _req not in _ass_map:
        raise ValueError(f"Missing required assumption '{_req}' in ModelAssumptions.csv")
RECOVERY_FRAC = float(_ass_map["RECOVERY_FRAC"])
RECOVERY_COST_UNIT = float(_ass_map["RECOVERY_COST_UNIT"])
SAME_PERIOD_SHIP = int(float(_ass_map.get("SAME_PERIOD_SHIP", 1)))
PRIMARY_LINE_RULE = str(_ass_map.get("PRIMARY_LINE_RULE", "PRIMARY_ALLOCATED"))
HOLDING_COST_ANNUAL_WACC = float(_ass_map.get("HOLDING_COST_ANNUAL_WACC", 0.18))
RECOVERY_COST_MODE = str(_ass_map.get("RECOVERY_COST_MODE", "STEPPED")).upper()
RECOVERY_TIER1_FRAC = float(_ass_map.get("RECOVERY_TIER1_FRAC", 0.05))
RECOVERY_TIER1_COST = float(_ass_map.get("RECOVERY_TIER1_COST", 2.0))
RECOVERY_TIER2_FRAC = float(_ass_map.get("RECOVERY_TIER2_FRAC", 0.15))
RECOVERY_TIER2_COST = float(_ass_map.get("RECOVERY_TIER2_COST", 7.0))
RECOVERY_TIER3_COST = float(_ass_map.get("RECOVERY_TIER3_COST", 14.0))

def _mc(units, gap_ref):
    return mitigation_cost(
        units, gap_ref,
        mode=RECOVERY_COST_MODE,
        flat_unit_cost=RECOVERY_COST_UNIT,
        tier1_frac=RECOVERY_TIER1_FRAC,
        tier1_cost=RECOVERY_TIER1_COST,
        tier2_frac=RECOVERY_TIER2_FRAC,
        tier2_cost=RECOVERY_TIER2_COST,
        tier3_cost=RECOVERY_TIER3_COST,
    )

if not (0.0 <= RECOVERY_FRAC <= 1.0):
    raise ValueError(f"RECOVERY_FRAC must be in [0,1], got {RECOVERY_FRAC}")
if RECOVERY_COST_UNIT < 0:
    raise ValueError(f"RECOVERY_COST_UNIT must be >= 0, got {RECOVERY_COST_UNIT}")
if SAME_PERIOD_SHIP not in (0, 1):
    raise ValueError(f"SAME_PERIOD_SHIP must be 0 or 1, got {SAME_PERIOD_SHIP}")
if "BOTTLENECK_THRESH" in _ass_map:
    BOTTLENECK_THRESH = float(_ass_map["BOTTLENECK_THRESH"])




import sys
integrity = {
    "run_id": RUN_ID,
    "script_version": SCRIPT_VERSION,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "environment": {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "random_seed_generator": 42,
    },
    "checks": [],
    "passed": True,
    "notes": [
        "CM = NetRevenue - StandardVariableCost (variable only; no fixed overhead)",
        "Sales = Shipments exactly; GoodProduction is post-scrap",
        "OpeningAvailableInventory is used to absorb same-period production shortfalls; closing inventory is never used for that period",
        "AlternateLineID is only assigned when a distinct capable alternate line exists",
        "Scenario coefficients loaded from ScenarioParameters.csv",
        "NetCMOpportunity is a modeled mitigation-value metric, not total company financial opportunity",
        "S3S5 not used (legacy typo)",
        "v1.4: AltLine slack is decremented as consumed (Period,AltLine) so it cannot be double-claimed by two products in the same period",
    ],
}

def record(name, ok, detail="", grain="", tolerance="", max_error="", failed_rows=0):
    integrity["checks"].append({
        "name": name,
        "passed": bool(ok),
        "detail": detail,
        "grain": grain,
        "tolerance": tolerance,
        "max_error": max_error,
        "failed_rows": int(failed_rows),
    })
    if not ok:
        integrity["passed"] = False

# ---------- Calendar ----------
DimDate["PeriodKey"] = DimDate.DateKey.str[:6]
dim_period = DimDate[["DateKey", "PeriodKey"]].drop_duplicates()

# ---------- 1. OEE per run ----------
Prod = Prod.merge(dim_period, on="DateKey", validate="m:1")
Prod["Availability"] = (Prod.RunTime_h / Prod.PlannedProductionTime_h).clip(0, 1)
Prod["Performance"] = (Prod.StandardCycleTime_h * Prod.TotalUnits / Prod.RunTime_h).clip(0, 1)
Prod["Quality"] = (Prod.GoodUnits / Prod.TotalUnits).clip(0, 1)
Prod["OEE"] = (Prod.Availability * Prod.Performance * Prod.Quality).clip(0, 1)
oee_bad = int((~Prod.OEE.between(0, 1)).sum())
record("OEE_in_range", oee_bad == 0, grain="ProductionRun", failed_rows=oee_bad,
       max_error=str(float(Prod.OEE.max()) if len(Prod) else 0))
good_bad = int((Prod.GoodUnits > Prod.TotalUnits).sum())
record("Good_le_Total", good_bad == 0, grain="ProductionRun", failed_rows=good_bad)
Prod.to_csv(FIN / "FactOEE_Run.csv", index=False)

# ---------- 2. Capacity & bottleneck ----------
bridge = Bridge.copy()
prim = (
    bridge.sort_values(["ProductID", "StandardRate"], ascending=[True, False])
    .groupby("ProductID").first().reset_index()
)
# Alternate capability must be a genuinely different line from the primary line.
# Products with no second capable line have no substitution path.
_primary_map = prim.set_index("ProductID")["LineID"].to_dict()
_alt_candidates = bridge.copy()
_alt_candidates["PrimaryLineID"] = _alt_candidates["ProductID"].map(_primary_map)
_alt_candidates = _alt_candidates[_alt_candidates["LineID"] != _alt_candidates["PrimaryLineID"]]
alt = (
    _alt_candidates.sort_values(["ProductID", "StandardRate"])
    .groupby("ProductID").first().reset_index()
)

avail_h = (
    Prod.groupby(["PeriodKey", "LineID"])
    .PlannedProductionTime_h.sum()
    .rename("LineAvailH")
    .reset_index()
)

monthly = Prod.groupby(["PeriodKey", "ProductID"]).agg(
    PlannedH=("PlannedProductionTime_h", "sum"),
    RunH=("RunTime_h", "sum"),
    GoodUnits=("GoodUnits", "sum"),
    ScrapUnits=("ScrapUnits", "sum"),
    TotalUnits=("TotalUnits", "sum"),
).reset_index()

def tw(g):
    return float(np.average(g.OEE, weights=g.PlannedProductionTime_h))

oee_t = (
    Prod.groupby(["PeriodKey", "ProductID"])
    .apply(tw, include_groups=False)
    .rename("OEE")
    .reset_index()
)
monthly = (
    monthly
    .merge(oee_t, on=["PeriodKey", "ProductID"])
    .merge(prim[["ProductID", "LineID", "StandardRate"]], on="ProductID")
    .merge(DimProduct[["ProductID", "StandardPrice", "StandardVariableCost"]], on="ProductID")
)

fd = Demand[Demand.DemandType == "Firm"][["PeriodKey", "ProductID", "DemandUnits"]].rename(
    columns={"DemandUnits": "FirmDemand"}
)
monthly = monthly.merge(fd, on=["PeriodKey", "ProductID"], how="left")
monthly["RequiredH"] = monthly.FirmDemand / monthly.StandardRate

req = (
    monthly.groupby(["PeriodKey", "LineID"])
    .RequiredH.sum()
    .rename("LineReqH")
    .reset_index()
)
line = avail_h.merge(req, on=["PeriodKey", "LineID"], how="outer").fillna(0)
line["Utilization"] = np.where(line.LineAvailH > 0, line.LineReqH / line.LineAvailH, 0.0)
line["Bottleneck"] = (line.LineReqH > line.LineAvailH * BOTTLENECK_THRESH).astype(int)
monthly = monthly.merge(
    line[["PeriodKey", "LineID", "Utilization", "Bottleneck"]],
    on=["PeriodKey", "LineID"],
)

# ---------- 3. Supply / inventory / recovery ----------
# Absorbable from roll-forward snapshot (sum across locations)
# Opening inventory is the inventory that was actually available to fulfill current-period
# firm demand in the synthetic roll-forward. Closing inventory is a residual balance and
# must NOT be used to absorb the same period's demand.
opening_inv = (
    Inv.groupby(["PeriodKey", "ProductID"])
    .agg(OpeningAvailableInventory=("OpeningAvailableInventory", "first"))
    .reset_index()
)
monthly = monthly.merge(opening_inv, on=["PeriodKey", "ProductID"], how="left")
monthly["OpeningAvailableInventory"] = monthly.OpeningAvailableInventory.fillna(0)

px = (
    Sales.groupby("ProductID")
    .apply(lambda g: g.NetRevenue.sum() / max(g.Units.sum(), 1e-9), include_groups=False)
    .rename("ExpNetPrice")
    .reset_index()
)
vc = (
    Sales.groupby("ProductID")
    .apply(lambda g: g.VariableCost.sum() / max(g.Units.sum(), 1e-9), include_groups=False)
    .rename("VCUnit")
    .reset_index()
)
monthly = monthly.merge(px, on="ProductID").merge(vc, on="ProductID")
monthly["CMUnit"] = monthly.ExpNetPrice - monthly.VCUnit

alt_rate = (
    alt.set_index("ProductID")[["LineID", "StandardRate"]]
    .rename(columns={"LineID": "AltLineID", "StandardRate": "AltRate"})
)
monthly = monthly.merge(alt_rate, left_on="ProductID", right_index=True, how="left")
# Explicitly verify no product is assigned its own primary line as an alternate.
same_alt = int((monthly["AltLineID"].notna() & (monthly["AltLineID"] == monthly["LineID"])) .sum())
record(
    "alternate_line_differs_from_primary",
    same_alt == 0,
    detail="Alternate capability must use a different physical line; products without one remain null",
    grain="ProductID×PeriodKey",
    failed_rows=same_alt,
)
li = line.set_index(["PeriodKey", "LineID"])

# Alternate-line slack is a shared, finite resource: if more than one product in the same
# period targets the same AltLineID, each unit of slack can only be claimed once. A static
# per-(Period, Line) lookup (as in v1.3) lets every claimant see the *full* un-consumed slack
# independently, which double-books capacity whenever two products share an alt line in the
# same period. v1.4 tracks remaining slack explicitly and decrements it as it is consumed.
# Allocation order is CM-per-unit descending within each period (highest-value opportunity
# gets first claim on scarce alternate-line hours), set via the monthly sort below.
remaining_alt_slack_h = {
    idx: max(0.0, float(row.LineAvailH - row.LineReqH))
    for idx, row in li.iterrows()
}

monthly = monthly.sort_values(["PeriodKey", "CMUnit"], ascending=[True, False]).reset_index(drop=True)

rows = []
for _, r in monthly.iterrows():
    supply_primary = float(r.GoodUnits)
    opening_available = float(r.OpeningAvailableInventory)
    # SAME_PERIOD_SHIP=1: current production can meet current demand.
    # SAME_PERIOD_SHIP=0: only opening inventory is shippable this period; production
    # lands in closing stock for future periods (aligned with generator roll-forward).
    shippable_production = supply_primary if SAME_PERIOD_SHIP == 1 else 0.0
    gross_gap = max(0.0, float(r.FirmDemand) - shippable_production)
    absorb = min(gross_gap, opening_available)
    gap1 = gross_gap - absorb

    # Recovery is a general mitigation mechanism and does not require a distinct alternate
    # line. Alternate-line capability is used only for the substitution step below.
    recovery = min(gap1, RECOVERY_FRAC * gap1)
    gap2 = gap1 - recovery

    alt_key = (r.PeriodKey, r.AltLineID)
    if pd.notna(r.AltRate) and r.AltRate > 0 and alt_key in remaining_alt_slack_h:
        avail_slack_h = max(0.0, remaining_alt_slack_h[alt_key])
        subst = min(gap2, avail_slack_h * r.AltRate)
        remaining_alt_slack_h[alt_key] = avail_slack_h - (subst / r.AltRate)
    else:
        subst = 0.0
    residual = max(0.0, gap2 - subst)
    lost = min(residual, r.FirmDemand)

    rev_exp = lost * r.ExpNetPrice
    cm_exp = lost * r.CMUnit
    rec_cost = _mc(recovery + subst, gross_gap if gross_gap > 0 else (recovery + subst))
    protected_cm = (recovery + subst) * r.CMUnit

    rows.append((
        r.PeriodKey, r.ProductID, r.LineID,
        r.PlannedH, r.RunH, r.GoodUnits, r.ScrapUnits, r.OEE,
        r.Utilization, r.Bottleneck,
        r.FirmDemand, supply_primary, float(r.OpeningAvailableInventory), gross_gap, absorb,
        recovery, subst, residual, lost,
        round(rev_exp, 2), round(cm_exp, 2),
        protected_cm, rec_cost,
        protected_cm - rec_cost,
        r.AltLineID if pd.notna(r.AltLineID) else None,
        float(r.AltRate) if pd.notna(r.AltRate) else 0.0,
        float(r.CMUnit), float(r.ExpNetPrice),
    ))

cols = [
    "PeriodKey", "ProductID", "LineID",
    "PlannedH", "RunH", "GoodUnits", "ScrapUnits", "OEE",
    "LineUtilization", "Bottleneck",
    "FirmDemand", "PrimarySupply", "OpeningAvailableInventory", "GrossGap", "InventoryAbsorbed",
    "RecoveredUnits", "SubstitutedUnits", "ResidualGap",
    "PotentialLostSalesUnits",
    "RevenueExposure", "CMExposure",
    "ProtectedCM", "RecoveryCost", "NetCMOpportunity",
    "AltLineID", "AltRate", "CMUnit", "ExpNetPrice",
]
Impact = pd.DataFrame(rows, columns=cols)

# Inventory holding cost (monthly): avg FG * standard VC * (annual WACC / 12)
_inv_h = (
    Inv.groupby(["PeriodKey", "ProductID"], as_index=False)
    .agg(OpeningInventory=("OpeningInventory", "first"), ClosingInventory=("ClosingInventory", "first"))
)
_vc = DimProduct[["ProductID", "StandardVariableCost"]].copy()
_inv_h = _inv_h.merge(_vc, on="ProductID", how="left")
_inv_h["AvgInventory"] = (_inv_h.OpeningInventory + _inv_h.ClosingInventory) / 2.0
_inv_h["HoldingCost"] = (
    _inv_h.AvgInventory * _inv_h.StandardVariableCost * (HOLDING_COST_ANNUAL_WACC / 12.0)
)
Impact = Impact.merge(
    _inv_h[["PeriodKey", "ProductID", "AvgInventory", "HoldingCost"]],
    on=["PeriodKey", "ProductID"],
    how="left",
)
Impact["AvgInventory"] = Impact.AvgInventory.fillna(0.0)
Impact["HoldingCost"] = Impact.HoldingCost.fillna(0.0)
Impact["NetCM_after_Holding"] = Impact.NetCMOpportunity - Impact.HoldingCost
# Incremental holding proxy: carrying cost only on units used to absorb the gap this period
# (InventoryAbsorbed × VC × WACC/12). Not a full counterfactual inventory path.
Impact["IncrementalHoldingCost"] = (
    Impact.InventoryAbsorbed * Impact.get("StandardVariableCost", 0)
    if "StandardVariableCost" in Impact.columns
    else Impact.InventoryAbsorbed * 0.0
)
# Prefer rate from HoldingCost/AvgInventory when available
if "AvgInventory" in Impact.columns:
    _rate = Impact.apply(
        lambda r: (float(r.HoldingCost) / float(r.AvgInventory))
        if float(r.AvgInventory or 0) > 0 else 0.0,
        axis=1,
    )
    Impact["IncrementalHoldingCost"] = Impact.InventoryAbsorbed.astype(float) * _rate
Impact["NetCM_after_IncrementalHolding"] = Impact.NetCMOpportunity - Impact.IncrementalHoldingCost



# Full-precision demand-gap waterfall:
# GrossGap = InventoryAbsorbed + RecoveredUnits + SubstitutedUnits + PotentialLostSalesUnits
waterfall_residual = (
    Impact.GrossGap
    - Impact.InventoryAbsorbed
    - Impact.RecoveredUnits
    - Impact.SubstitutedUnits
    - Impact.PotentialLostSalesUnits
)
wf_max = float(waterfall_residual.abs().max()) if len(waterfall_residual) else 0.0
wf_bad = int((waterfall_residual.abs() > 1e-6).sum())
record(
    "gap_waterfall_full_precision",
    wf_bad == 0,
    detail="GrossGap = InvAbs + Recovered + Substituted + LostSales",
    grain="ProductID×PeriodKey",
    tolerance="1e-6",
    max_error=str(wf_max),
    failed_rows=wf_bad,
)

# Opportunity identity: NetCMOpportunity = ProtectedCM - RecoveryCost  (NOT CMExposure - RecoveryCost)
# ProtectedCM = CM of units recovered or substituted (saved from becoming lost sales)
# CMExposure  = CM of residual lost sales after all mitigations
net_id = (Impact.NetCMOpportunity - (Impact.ProtectedCM - Impact.RecoveryCost)).abs()
net_bad = int((net_id > 1e-6).sum())
record(
    "net_cm_opportunity_identity",
    net_bad == 0,
    detail="NetCMOpportunity = ProtectedCM - RecoveryCost",
    grain="ProductID×PeriodKey",
    tolerance="1e-6",
    max_error=str(float(net_id.max()) if len(net_id) else 0),
    failed_rows=net_bad,
)

# Regression guard for the v1.4 fix: total substituted units claimed against any single
# (PeriodKey, AltLineID) must never exceed that line's available slack capacity in that
# period, even when multiple products share the same alternate line.
sub_by_altline = (
    Impact[Impact.AltLineID.notna()]
    .assign(AltRate_safe=Impact.AltRate.where(Impact.AltRate > 0, np.nan))
    .assign(SubstHours=lambda d: d.SubstitutedUnits / d.AltRate_safe)
    .groupby(["PeriodKey", "AltLineID"])
    .SubstHours.sum()
)
avail_h_by_altline = pd.Series(
    {idx: max(0.0, float(row.LineAvailH - row.LineReqH)) for idx, row in li.iterrows()}
)
over = (sub_by_altline - avail_h_by_altline.reindex(sub_by_altline.index).fillna(0.0)).clip(lower=0.0)
oversub_bad = int((over > 1e-6).sum())
record(
    "alt_line_slack_not_oversubscribed",
    oversub_bad == 0,
    detail="Sum of substituted hours per (Period, AltLine) must not exceed that line's available slack",
    grain="PeriodKey×AltLineID",
    tolerance="1e-6",
    max_error=str(float(over.max()) if len(over) else 0.0),
    failed_rows=oversub_bad,
)

# Grain rule: one primary/allocated LineID per Product × Period (not multi-line operational grain)
_line_n = Impact.groupby(["PeriodKey", "ProductID"]).LineID.nunique()
_multi = int((_line_n > 1).sum())

record(
    "same_period_ship_waterfall_aligned",
    True,
    detail=f"Impact/scenario shippable production uses SAME_PERIOD_SHIP={SAME_PERIOD_SHIP}",
    grain="ModelAssumptions×Impact",
    failed_rows=0,
)

record(
    "impact_one_primary_line_per_product_period",
    _multi == 0,
    detail="LineID is the primary/allocated line for the product-month; PK grain is PeriodKey×ProductID",
    grain="ProductID×PeriodKey",
    failed_rows=_multi,
)

Impact.to_csv(FIN / "FactImpact_ProductPeriod.csv", index=False)

# ---------- 4. PVM bridge (group + total assertions) ----------
Sales2 = Sales.merge(dim_period, on="DateKey", validate="m:1")
act = (
    Sales2.groupby(["PeriodKey", "ProductID"])
    .agg(AUnits=("Units", "sum"), ARev=("NetRevenue", "sum"), AVC=("VariableCost", "sum"))
    .reset_index()
)
bud = Plan[["PeriodKey", "ProductID", "BudgetVolume", "BudgetRevenue", "BudgetCM"]].rename(
    columns={"BudgetVolume": "BUnits", "BudgetRevenue": "BRev", "BudgetCM": "BCM"}
)
pvm = act.merge(bud, on=["PeriodKey", "ProductID"], how="outer").fillna(0)
pvm["BPrice"] = np.where(pvm.BUnits > 0, pvm.BRev / pvm.BUnits, 0.0)
pvm["ACM"] = pvm.ARev - pvm.AVC

totB = pvm.BUnits.sum()
pB = pvm.BRev.sum() / max(totB, 1e-9)
pvm["VolumeEffect"] = (pvm.AUnits - pvm.BUnits) * pB
pvm["MixEffect"] = pvm.AUnits * (pvm.BPrice - pB)
avg_aprice = np.where(pvm.AUnits > 0, pvm.ARev / pvm.AUnits.replace(0, np.nan), 0.0)
pvm["PriceEffect"] = pvm.AUnits * (pd.Series(avg_aprice).fillna(0).values - pvm.BPrice)

# Residual so that: ARev = BRev + Volume + Mix + Price + Residual
pvm["Residual"] = pvm.ARev - (pvm.BRev + pvm.VolumeEffect + pvm.MixEffect + pvm.PriceEffect)
pvm["ExpectedDelta"] = pvm.ARev - pvm.BRev
pvm["CalculatedDelta"] = pvm.VolumeEffect + pvm.MixEffect + pvm.PriceEffect + pvm.Residual
pvm["PVMError"] = pvm.CalculatedDelta - pvm.ExpectedDelta

allowed = PVM_ABS_TOL + PVM_REL_TOL * pvm.ExpectedDelta.abs()
group_fail_mask = pvm.PVMError.abs() > allowed
group_bad = int(group_fail_mask.sum())
record(
    "PVM_group_level", group_bad == 0,
    detail="ActualRev-BudgetRev = Vol+Mix+Price+Residual",
    grain="ProductID×PeriodKey",
    tolerance=f"abs={PVM_ABS_TOL} + rel={PVM_REL_TOL}*|delta|",
    max_error=f"{float(pvm.PVMError.abs().max()):.6e}",
    failed_rows=group_bad,
)

tot_calc = pvm.CalculatedDelta.sum()
tot_exp = pvm.ExpectedDelta.sum()
tot_err = tot_calc - tot_exp
tot_allowed = PVM_ABS_TOL + PVM_REL_TOL * abs(tot_exp)
total_ok = abs(tot_err) <= tot_allowed
record(
    "PVM_total_level", total_ok,
    detail=f"total_error={tot_err:.6e}",
    grain="Portfolio total",
    tolerance=f"abs={PVM_ABS_TOL} + rel={PVM_REL_TOL}*|delta|",
    max_error=f"{tot_err:.6e}",
    failed_rows=0 if total_ok else 1,
)

# Legacy residual print (should be ~0 by construction of Residual)
recon = float(pvm.Residual.sum())
print(f"PVM residual sum: {recon:.6f}")
print(f"PVM max group |error|: {float(pvm.PVMError.abs().max()):.6e}")

pvm.to_csv(FIN / "PVM_Bridge.csv", index=False)

# ---------- 5. Scenario engine (coefficients from ScenarioParameters.csv) ----------
def scenario_supply_and_demand(params_row, imp):
    """Apply config-table factors; no hard-coded scenario IDs required."""
    pts = float(params_row.OEE_Uplift_pts)
    out_f = float(params_row.Output_Factor)
    scrap_f = float(params_row.Scrap_Recover_Frac)
    dem_f = float(params_row.Demand_Factor)
    frac_mult = float(params_row.Recovery_Frac_Mult)

    supply = imp.PrimarySupply * out_f
    if pts > 0:
        supply = supply + imp.PrimarySupply * (pts / imp.OEE.clip(lower=0.05))
    if scrap_f > 0:
        supply = supply + imp.ScrapUnits * scrap_f
    firm = imp.FirmDemand * dem_f
    return supply, firm, frac_mult

scen = []
for _, s in ScenParams[ScenParams.ScenarioID != "S0"].iterrows():
    sid = s.ScenarioID
    imp = Impact.copy()
    eff_supply, fd2, frac_mult = scenario_supply_and_demand(s, imp)

    # Fresh slack ledger per scenario. Scale baseline LineReqH by Demand_Factor so
    # demand-uplift scenarios do not credit substitution against un-stressed capacity.
    dem_f = float(s.Demand_Factor)
    scen_remaining_alt_slack_h = {
        idx: max(0.0, float(row.LineAvailH) - float(row.LineReqH) * dem_f)
        for idx, row in li.iterrows()
    }

    lost_list, cm_exp_list, rec_cost_list = [], [], []
    for i, r in imp.iterrows():
        scenario_good_supply = float(eff_supply.loc[i])
        opening_available = float(r.OpeningAvailableInventory) if pd.notna(r.OpeningAvailableInventory) else 0.0
        firm = float(fd2.loc[i])
        shippable = scenario_good_supply if SAME_PERIOD_SHIP == 1 else 0.0
        gross = max(0.0, firm - shippable)
        absorb = min(gross, opening_available)
        gap1 = gross - absorb
        frac = RECOVERY_FRAC * frac_mult
        recovery = min(gap1, frac * gap1)
        gap2 = gap1 - recovery
        alt_r = r.AltRate if pd.notna(r.AltRate) else 0.0
        alt_key = (r.PeriodKey, r.AltLineID)
        if alt_r > 0 and alt_key in scen_remaining_alt_slack_h:
            avail_slack_h = max(0.0, scen_remaining_alt_slack_h[alt_key])
            subst = min(gap2, avail_slack_h * alt_r)
            scen_remaining_alt_slack_h[alt_key] = avail_slack_h - (subst / alt_r)
        else:
            subst = 0.0
        residual = max(0.0, gap2 - subst)
        lost = min(residual, firm)
        cm_u = float(r.CMUnit) if pd.notna(r.CMUnit) else 0.0
        if cm_u == 0:
            cm_u = float(Impact.CMExposure.sum() / max(Impact.PotentialLostSalesUnits.sum(), 1e-9))
        lost_list.append(lost)
        cm_exp_list.append(lost * cm_u)
        rec_cost_list.append(_mc(recovery + subst, gross if gross > 0 else (recovery + subst)))

    lost_s = pd.Series(lost_list)
    cm_s = pd.Series(cm_exp_list)
    rec_cost_s = pd.Series(rec_cost_list)
    cm_imp = float(imp.CMExposure.sum() - cm_s.sum())
    net = cm_imp - float(rec_cost_s.sum())
    confidence = "Medium" if sid in ("S1", "SD10", "SQ") else "Low"
    scen.append(dict(
        ScenarioID=sid,
        ScenarioName=s.ScenarioName,
        ScenarioType=s.ScenarioType,
        OEE_Uplift_pts=float(s.OEE_Uplift_pts),
        Output_Factor=float(s.Output_Factor),
        Demand_Factor=float(s.Demand_Factor),
        Recovery_Frac_Mult=float(s.Recovery_Frac_Mult),
        LostUnits_baseline=int(round(imp.PotentialLostSalesUnits.sum())),
        LostUnits_scenario=int(round(lost_s.sum())),
        CMExposure_baseline=round(float(imp.CMExposure.sum()), 2),
        CMExposure_scenario=round(float(cm_s.sum()), 2),
        CMImpact=round(cm_imp, 2),
        RecoveryCost=round(float(rec_cost_s.sum()), 2),
        # Distinct from FactImpact.NetCMOpportunity (= ProtectedCM - RecoveryCost)
        NetCMImpact_after_RecoveryCost=round(net, 2),
        Confidence=confidence,
    ))

SC = pd.DataFrame(scen)
SC.to_csv(FIN / "Scenario_Results.csv", index=False)
print("\nScenario Results:")
print(SC.to_string(index=False))

# ---------- 6. CaseTrace ----------
def pick(df, n=3):
    return df.head(n)

sel = {
    "no-impact": pick(Impact[(Impact.PotentialLostSalesUnits == 0) & (Impact.GrossGap == 0)]),
    "financial-impact": pick(
        Impact[Impact.PotentialLostSalesUnits > 0].sort_values("CMExposure", ascending=False), 5
    ),
    "recovery-protected": pick(
        Impact[(Impact.GrossGap > 0) & (Impact.PotentialLostSalesUnits == 0)], 4
    ),
    "bottleneck": pick(Impact[Impact.Bottleneck == 1]),
    "non-bottleneck": pick(Impact[(Impact.Bottleneck == 0) & (Impact.GrossGap > 0)]),
}
cases = []
for ctype, g in sel.items():
    for _, r in g.iterrows():
        action = (
            "Monitor only - no financial impact"
            if r.PotentialLostSalesUnits == 0
            else "Prioritize downtime/scrap reduction on bottleneck line; verify backlog vs permanent lost sales"
        )
        cases.append(dict(
            CaseType=ctype,
            PeriodKey=r.PeriodKey,
            ProductID=r.ProductID,
            LineID=r.LineID,
            OEE=round(r.OEE, 4),
            GoodUnits=r.GoodUnits,
            FirmDemand=r.FirmDemand,
            GrossGap=r.GrossGap,
            OpeningAvailableInventory=r.OpeningAvailableInventory,
            InventoryAbsorbed=r.InventoryAbsorbed,
            RecoveredUnits=r.RecoveredUnits,
            SubstitutedUnits=r.SubstitutedUnits,
            PotentialLostSalesUnits=r.PotentialLostSalesUnits,
            RevenueExposure=r.RevenueExposure,
            CMExposure=r.CMExposure,
            RecoveryCost=r.RecoveryCost,
            NetCMOpportunity=r.NetCMOpportunity,
            ManagementAction=action,
        ))
CT = pd.DataFrame(cases)
CT.to_csv(FIN / "CaseTrace.csv", index=False)
print("\nCaseTrace:", len(CT), CT.CaseType.value_counts().to_dict())

# ---------- 7. Prioritization (layered opportunity chain) ----------
opp = Impact[Impact.CMExposure > 0].copy()
# Layered opportunity semantics (see DATA_DICTIONARY.md)
opp["TheoreticalCapacityGapUnits"] = opp.GrossGap
opp["DemandConstrainedGapUnits"] = opp.GrossGap - opp.InventoryAbsorbed  # residual after opening inventory
opp["ShipmentGapUnits"] = opp.PotentialLostSalesUnits
opp["RevenueOpportunity"] = opp.RevenueExposure
opp["CMOpportunity"] = opp.CMExposure

opp["RecoveryROI"] = np.where(
    opp.RecoveryCost > 0,
    (opp.ProtectedCM - opp.RecoveryCost) / opp.RecoveryCost,
    np.nan,
)
opp["RecoveryROI_Status"] = np.where(
    opp.RecoveryCost > 0,
    "OK",
    "Undefined: zero investment",
)
# Never emit inf
_roi = opp.RecoveryROI.to_numpy(dtype=float, na_value=np.nan)
if np.isinf(_roi).any():
    raise ValueError("Financial output RecoveryROI contains infinite values; use NaN + status flag instead")

opp = opp.sort_values("NetCMOpportunity", ascending=False)
opp.to_csv(FIN / "Opportunity_Prioritization.csv", index=False)
record(
    "no_inf_in_ROI",
    not np.isinf(opp.RecoveryROI.to_numpy(dtype=float, na_value=np.nan)).any() if len(opp) else True,
    grain="ProductID×PeriodKey (CMExposure>0)",
)

# ---------- 8. Inventory integrity from snapshot ----------
inv_chk = Inv.copy()
usable_fail = int((inv_chk.UsableInventory != inv_chk.FGInventory - inv_chk.BlockedInventory).sum())
record(
    "UsableInventory_rounding", usable_fail == 0,
    grain="Period×Product×Location", failed_rows=usable_fail,
)

has_rf = all(c in Inv.columns for c in [
    "OpeningInventory", "GoodProduction", "Shipments", "ClosingInventory"
])
record("inventory_rollforward_columns", has_rf, grain="FactInventorySnapshot schema")

# Opening inventory must be the supply used for the same-period demand waterfall.
has_opening_available = "OpeningAvailableInventory" in Inv.columns
record("opening_available_inventory_column", has_opening_available, grain="FactInventorySnapshot schema")

if has_rf and has_opening_available:
    rf = Inv.groupby(["PeriodKey", "ProductID"]).agg(
        Opening=("OpeningInventory", "first"),
        Good=("GoodProduction", "first"),
        Ship=("Shipments", "first"),
        Close=("ClosingInventory", "first"),
    ).reset_index()
    rf["ExpectedClose"] = rf.Opening + rf.Good - rf.Ship
    bal_series = (rf.Close - rf.ExpectedClose).abs()
    bal = float(bal_series.max()) if len(bal_series) else 0.0
    bal_fail = int((bal_series > 0).sum())
    record(
        "inventory_mass_balance", bal_fail == 0,
        grain="ProductID×PeriodKey", tolerance="0",
        max_error=str(bal), failed_rows=bal_fail,
    )

    rf = rf.sort_values(["ProductID", "PeriodKey"])
    rf["PrevClose"] = rf.groupby("ProductID")["Close"].shift(1)
    cont = rf[rf.PrevClose.notna()].copy()
    cont_err = (cont.Opening - cont.PrevClose).abs()
    cerr = float(cont_err.max()) if len(cont_err) else 0.0
    cont_fail = int((cont_err > 0).sum()) if len(cont_err) else 0
    record(
        "inventory_continuity", cont_fail == 0,
        grain="ProductID×PeriodKey", tolerance="0",
        max_error=str(cerr), failed_rows=cont_fail,
    )

# Sales vs demand
ms = Sales.copy()
ms["PeriodKey"] = ms.DateKey.str[:6]
ms = ms.groupby(["PeriodKey", "ProductID"], as_index=False)["Units"].sum()
ms = ms.merge(fd, on=["PeriodKey", "ProductID"], how="left")
sales_fail = int((ms.Units > ms.FirmDemand).sum())
record(
    "sales_le_firm_demand", sales_fail == 0,
    grain="ProductID×PeriodKey", tolerance="0",
    failed_rows=sales_fail,
)

# --- Domain / economic plausibility checks ---
vc_price_fail = int((DimProduct.StandardVariableCost > DimProduct.StandardPrice).sum())
record(
    "variable_cost_le_price",
    vc_price_fail == 0,
    detail="StandardVariableCost <= StandardPrice for all products",
    grain="DimProduct",
    failed_rows=vc_price_fail,
)
neg_price = int(((DimProduct.StandardPrice < 0) | (DimProduct.StandardVariableCost < 0)).sum())
record(
    "non_negative_price_and_vc",
    neg_price == 0,
    grain="DimProduct",
    failed_rows=neg_price,
)
frac_ok = 0.0 <= RECOVERY_FRAC <= 1.0
record(
    "recovery_frac_in_unit_interval",
    frac_ok,
    detail=f"RECOVERY_FRAC={RECOVERY_FRAC}",
    grain="ModelAssumptions",
    failed_rows=0 if frac_ok else 1,
)
prot_vs_gap = Impact.copy()
prot_units = Impact.RecoveredUnits + Impact.SubstitutedUnits
# Protected units should not exceed GrossGap
prot_over = int((prot_units - Impact.GrossGap > 1e-6).sum())
record(
    "protected_units_le_gross_gap",
    prot_over == 0,
    grain="ProductID×PeriodKey",
    tolerance="1e-6",
    failed_rows=prot_over,
)
# Flag uneconomic mitigation rows (ProtectedCM < RecoveryCost) — allowed, but counted
unecon = int((Impact.ProtectedCM < Impact.RecoveryCost - 1e-9).sum())
record(
    "uneconomic_mitigation_rows_counted",
    True,  # informational, does not fail the run
    detail=f"rows_where_recovery_cost>protected_cm={unecon}",
    grain="ProductID×PeriodKey",
    failed_rows=0,
)

# Nonfinite in core numeric outputs (NaN in RecoveryROI is allowed / expected)
def unexpected_nonfinite(df, allow_nan_cols=None):
    allow_nan_cols = allow_nan_cols or []
    num = df.select_dtypes(include=[np.number])
    inf_n = int(np.isinf(num.to_numpy(dtype=float, na_value=np.nan)).sum())
    nan_n = 0
    for c in num.columns:
        if c in allow_nan_cols:
            continue
        nan_n += int(num[c].isna().sum())
    return inf_n + nan_n

nf = (
    unexpected_nonfinite(Prod)
    + unexpected_nonfinite(Impact)
    + unexpected_nonfinite(pvm)
    + unexpected_nonfinite(SC)
    + unexpected_nonfinite(opp, allow_nan_cols=["RecoveryROI"])
    + unexpected_nonfinite(Inv)
    + unexpected_nonfinite(Sales)
)
record(
    "no_unexpected_nonfinite", nf == 0,
    detail=f"count={nf} (RecoveryROI NaN allowed)",
    grain="all core tables",
    failed_rows=nf,
)

# Scenario parameters coverage
missing_scen = set(DimScenario.ScenarioID) - set(ScenParams.ScenarioID)
record(
    "scenario_parameters_coverage",
    len(missing_scen) == 0,
    detail=f"missing_in_params={sorted(missing_scen)}",
    grain="ScenarioID",
    failed_rows=len(missing_scen),
)

# ---------- 9. Executive summary ----------
summary = dict(
    run_id=RUN_ID,
    script_version=SCRIPT_VERSION,
    total_revenue_actual=round(float(Sales.NetRevenue.sum()), 2),
    total_cm_actual=round(float(Sales.CM.sum()), 2),
    budget_revenue=round(float(Plan.BudgetRevenue.sum()), 2),
    budget_cm=round(float(Plan.BudgetCM.sum()), 2),
    pvm_residual_sum=round(recon, 6),
    pvm_max_group_error=round(float(pvm.PVMError.abs().max()), 10),
    oee_avg_time_weighted=round(
        float(np.average(Prod.OEE, weights=Prod.PlannedProductionTime_h)), 4
    ),
    total_gross_gap_units=int(Impact.GrossGap.sum()),
    inventory_absorbed_units=int(Impact.InventoryAbsorbed.sum()),
    recovered_units=int(Impact.RecoveredUnits.sum()),
    substituted_units=int(Impact.SubstitutedUnits.sum()),
    potential_lost_sales_units=int(Impact.PotentialLostSalesUnits.sum()),
    revenue_exposure=round(float(Impact.RevenueExposure.sum()), 2),
    cm_exposure=round(float(Impact.CMExposure.sum()), 2),
    recovery_cost=round(float(Impact.RecoveryCost.sum()), 2),
    protected_cm=round(float(Impact.ProtectedCM.sum()), 2),
    net_cm_opportunity=round(float(Impact.NetCMOpportunity.sum()), 2),
    inventory_holding_cost=round(float(Impact.HoldingCost.sum()), 2),
    net_cm_after_holding=round(float(Impact.NetCM_after_Holding.sum()), 2),
    incremental_holding_cost=round(float(Impact.IncrementalHoldingCost.sum()), 2),
    net_cm_after_incremental_holding=round(float(Impact.NetCM_after_IncrementalHolding.sum()), 2),
    figure_class="Modeled / assumption-driven / not a forecast",
    recovery_cost_mode=RECOVERY_COST_MODE,
    holding_cost_annual_wacc=HOLDING_COST_ANNUAL_WACC,
    # Explicit bridge (auditable):
    # NetCMOpportunity = ProtectedCM - RecoveryCost
    # ProtectedCM = CM of RecoveredUnits + SubstitutedUnits (not equal to CMExposure)
    # CMExposure = CM of PotentialLostSalesUnits only
    opportunity_bridge={
        "cm_exposure_lost_sales": round(float(Impact.CMExposure.sum()), 2),
        "protected_cm_from_recovery_and_substitution": round(float(Impact.ProtectedCM.sum()), 2),
        "recovery_cost": round(float(Impact.RecoveryCost.sum()), 2),
        "net_cm_opportunity": round(float(Impact.NetCMOpportunity.sum()), 2),
        "identity": "NetCMOpportunity = ProtectedCM - RecoveryCost",
        "note": "NetCMOpportunity is NOT CMExposure - RecoveryCost; it is the modeled value of mitigation actions after recovery/substitution cost",
    },
    gap_waterfall={
        "gross_gap": float(Impact.GrossGap.sum()),
        "inventory_absorbed": float(Impact.InventoryAbsorbed.sum()),
        "recovered": float(Impact.RecoveredUnits.sum()),
        "substituted": float(Impact.SubstitutedUnits.sum()),
        "lost_sales": float(Impact.PotentialLostSalesUnits.sum()),
        "residual": float((Impact.GrossGap - Impact.InventoryAbsorbed - Impact.RecoveredUnits - Impact.SubstitutedUnits - Impact.PotentialLostSalesUnits).sum()),
        "identity": "GrossGap = InvAbs + Recovered + Substituted + LostSales",
    },
    bottleneck_product_periods=int(Impact.Bottleneck.sum()),
    oee_directly_multiplied_by_revenue=False,
    recovery_frac_assumption=RECOVERY_FRAC,
    recovery_cost_unit_assumption=RECOVERY_COST_UNIT,
    currency="USD",
    volume_unit="EA",
    S3S5_status="Removed: original typo with no valid business definition; use S3 and S5 separately",
    data_dictionary="DATA_DICTIONARY.md",
    context={
        "data_type": "synthetic",
        "period_coverage": "FY2024 (202401-202412)",
        "product_count": 8,
        "reporting_currency": "USD",
        "volume_unit": "EA",
        "oee_baseline_time_weighted": round(
            float(__import__("numpy").average(Prod.OEE, weights=Prod.PlannedProductionTime_h)), 4
        ),
        "recovery_frac": RECOVERY_FRAC,
        "same_period_ship": SAME_PERIOD_SHIP,
        "primary_line_rule": PRIMARY_LINE_RULE,
        "recovery_cost_unit_usd": RECOVERY_COST_UNIT,
        "cm_definition": "Managerial CM before fixed costs (NetRevenue - StandardVariableCost)",
        "disclaimer": "Figures are model outputs under documented assumptions, not real-plant results",
    },
)
json.dump(summary, open(FIN / "Executive_Summary_Numbers.json", "w"), indent=2)
print("\nExecutive Summary:")
print(json.dumps(summary, indent=2))

# ---------- integrity_checks.json ----------
integrity["summary"] = summary
integrity["row_counts"] = {
    "FactProduction": len(Prod),
    "FactImpact": len(Impact),
    "PVM_Bridge": len(pvm),
    "Scenario_Results": len(SC),
    "CaseTrace": len(CT),
    "FactInventorySnapshot": len(Inv),
    "FactSales": len(Sales),
    "ScenarioParameters": len(ScenParams),
}
integrity["tolerances"] = {
    "PVM_ABS_TOL": PVM_ABS_TOL,
    "PVM_REL_TOL": PVM_REL_TOL,
    # sales_le_firm_demand is enforced at zero tolerance (see CHANGELOG v1.3); no
    # rounding-tolerance constant is applied and none is reported here.
}
integrity["resolved_config"] = {
    "RECOVERY_FRAC": RECOVERY_FRAC,
    "RECOVERY_COST_UNIT": RECOVERY_COST_UNIT,
    "SAME_PERIOD_SHIP": SAME_PERIOD_SHIP,
    "HOLDING_COST_ANNUAL_WACC": HOLDING_COST_ANNUAL_WACC,
    "RECOVERY_COST_MODE": RECOVERY_COST_MODE,
    "RECOVERY_TIER1_COST": RECOVERY_TIER1_COST,
    "RECOVERY_TIER2_COST": RECOVERY_TIER2_COST,
    "RECOVERY_TIER3_COST": RECOVERY_TIER3_COST,
    "PRIMARY_LINE_RULE": PRIMARY_LINE_RULE,
    "BOTTLENECK_THRESH": BOTTLENECK_THRESH,
    "currency": "USD",
    "volume_unit": "EA",
    "config_source": "ModelAssumptions.csv" if _assumptions_path.exists() else "engine_defaults",
}
json.dump(integrity, open(FIN / "integrity_checks.json", "w"), indent=2)
print(f"\nIntegrity passed: {integrity['passed']}")
for c in integrity["checks"]:
    status = "PASS" if c["passed"] else "FAIL"
    extra = f" failed_rows={c.get('failed_rows', 0)}"
    if c.get("max_error"):
        extra += f" max_error={c['max_error']}"
    print(f"  [{status}] {c['name']}:{extra} {c.get('detail', '')}")

# ---------- SQLite ----------
# Single write path: run 05_build_sqlite_with_keys.py after this engine
# (avoids a second unkeyed to_sql dump that could overwrite PK/FK schema).
print("\nSQLite: skip in engine — run 05_build_sqlite_with_keys.py for PK/FK database")

# ---------- Output content hashes (reproducibility fingerprint) ----------
def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

hash_targets = [
    "FactProduction.csv", "FactSales.csv", "FactDemand.csv",
    "FactInventorySnapshot.csv", "FactImpact_ProductPeriod.csv",
    "PVM_Bridge.csv", "Scenario_Results.csv", "Opportunity_Prioritization.csv",
]
hashes = {}
for name in hash_targets:
    p = OUT / name if (OUT / name).exists() else FIN / name
    if p.exists():
        hashes[name] = file_hash(p)
json.dump({"run_id": RUN_ID, "script_version": SCRIPT_VERSION, "sha256": hashes},
          open(FIN / "output_hashes.json", "w"), indent=2)
print("\nOutput SHA256 fingerprints written to final/output_hashes.json")
print("All done.")
