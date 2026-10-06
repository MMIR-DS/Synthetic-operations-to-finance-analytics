"""Build synthetic OEE -> Revenue -> CM dataset for an *imaginary dairy factory*.

Domain skin: fresh milk / yogurt / cheese packing, cold stores, CIP & changeover.
Core analytics unchanged (gap waterfall, CM, stepped recovery, holding).

Original header: synthetic OEE -> Revenue -> CM dataset (corrected pipeline).

Fixes vs original:
- Paths relative to __file__
- True inventory roll-forward: Closing = Opening + GoodProduction - Shipments
- Opening(t+1) = Closing(t)
- UsableInventory from final rounded FG - Blocked with assertion
- Sales = min(FirmDemand, Opening + GoodProduction)  (no double-counting with engine)
- OpeningAvailableInventory explicitly identifies same-period inventory supply
- Sales transaction allocation preserves shipment totals exactly (no rounding drift)
- Strong integrity assertions
- DimScenario: S3S5 removed (was typo); S3 and S5 kept as separate scenarios
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEED)

# ---------- DimDate ----------
dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
pd.DataFrame({
    "DateKey": [d.strftime("%Y%m%d") for d in dates],
    "Date": dates.strftime("%Y-%m-%d"),
    "Month": dates.month,
    "Year": dates.year,
    "Quarter": ["Q" + str(d.quarter) for d in dates],
    "FiscalPeriod": ["FY24-M%02d" % d.month for d in dates],
    "FiscalYear": "FY2024",
}).to_csv(OUT / "DimDate.csv", index=False)

# ---------- DimProduct + COGS components (L1) ----------
# Model $ scale kept for readable portfolio totals; *shares* calibrated to public dairy structure:
# - Fluid whole milk: farm share of retail ~49% (USDA ERS 2024: farm $1.97 of ~$3.98/gal)
# - Processor variable cost: raw milk dominates (~70-80% of plant variable cost for fluid)
# - Cultured/cheese: lower raw share of retail, higher process/pack intensity
# Sources: USDA ERS farm-share notes; industry fluid "raw ~half of retail / majority of plant VC"
# StandardVariableCost = RawMilk + Packaging + ProcessingEnergy + OtherVariable (identity)

# ProductID, Name, Family, Category, UoM, Price, ShelfLifeDays, LitersPerUnit,
#   RawMilk, Packaging, ProcessingEnergy, OtherVariable  (all model-USD per EA)
prod_specs = [
    ("P1", "Fresh Full Cream Milk 1L", "FreshMilk", "FreshMilk", "EA", 100.0, 12, 1.0,
        43.0, 9.0, 6.0, 4.0),   # VC=62; raw ~69% of VC; raw/price=43% (near farm share)
    ("P2", "Fresh Low Fat Milk 1L", "FreshMilk", "FreshMilk", "EA", 85.0, 12, 1.0,
        35.0, 8.0, 5.0, 2.0),   # VC=50
    ("P3", "Fresh Full Cream Milk 2L", "FreshMilk", "FreshMilk", "EA", 120.0, 12, 2.0,
        55.0, 12.0, 8.0, 5.0),  # VC=80; 2L pack efficiency
    ("P4", "Stirred Yogurt 500g", "Yogurt", "Cultured", "EA", 60.0, 21, 0.5,
        20.0, 10.0, 5.0, 3.0),  # VC=38; more pack share
    ("P5", "Greek Yogurt 400g", "Yogurt", "Cultured", "EA", 75.0, 25, 0.4,
        26.0, 12.0, 7.0, 4.0),  # VC=49
    ("P6", "Drinkable Yogurt 1L", "Yogurt", "Cultured", "EA", 95.0, 18, 1.0,
        38.0, 14.0, 9.0, 5.0),  # VC=66
    ("P7", "White Cheese 400g", "Cheese", "Cheese", "EA", 150.0, 45, 0.4,
        48.0, 12.0, 32.0, 13.0), # VC=105; process-heavy (aging/yield)
    ("P8", "Butter 250g", "Butter", "Butter", "EA", 180.0, 60, 0.25,
        85.0, 10.0, 25.0, 10.0), # VC=130; high cream/farm content
]
dp = pd.DataFrame(prod_specs, columns=[
    "ProductID", "ProductName", "ProductFamily", "ProductCategory",
    "UnitOfMeasure", "StandardPrice", "ShelfLifeDays", "LitersPerUnit",
    "RawMilkCost", "PackagingCost", "ProcessingEnergyCost", "OtherVariableCost",
])
dp["StandardVariableCost"] = (
    dp.RawMilkCost + dp.PackagingCost + dp.ProcessingEnergyCost + dp.OtherVariableCost
)
# Guard identity
assert (dp.StandardVariableCost > 0).all()
dp["StandardCM"] = dp.StandardPrice - dp.StandardVariableCost
dp["CM_Pct_of_Price"] = (dp.StandardCM / dp.StandardPrice).round(4)
dp["RawMilk_Share_of_Price"] = (dp.RawMilkCost / dp.StandardPrice).round(4)
dp["Plant"] = "North Valley Dairy (synthetic)"
dp["CostBasisNote"] = "Model-USD; component shares aligned to public dairy farm/processor structure"
dp.to_csv(OUT / "DimProduct.csv", index=False)
sp = dp.set_index("ProductID")

# ---------- Bridge_BOM (shallow 1-level recipe) ----------
# Illustrative quantities; costs roll from DimProduct components (not re-priced here)
bom_rows = []
for _, r in dp.iterrows():
    pid, lit = r.ProductID, float(r.LitersPerUnit)
    # Raw milk input ≈ liters in pack (yogurt/cheese approximate milk input factor)
    milk_factor = {"FreshMilk": 1.0, "Yogurt": 1.05, "Cheese": 4.0, "Butter": 6.0}.get(
        r.ProductCategory if "ProductCategory" in r.index else r.ProductFamily, 1.0
    )
    # ProductCategory column exists
    cat = r.ProductCategory
    milk_factor = {"FreshMilk": 1.0, "Cultured": 1.08, "Cheese": 4.2, "Butter": 6.5}.get(cat, 1.0)
    bom_rows.append((pid, "RAW-MILK", "Raw milk", "L", round(lit * milk_factor, 3), "RawMilkCost"))
    bom_rows.append((pid, "PACK-PRIMARY", "Primary pack (carton/cup/tub)", "EA", 1.0, "PackagingCost"))
    if cat in ("Cultured", "Cheese"):
        bom_rows.append((pid, "CULTURE-AUX", "Culture / salt / auxiliary", "LOT", 1.0, "OtherVariableCost"))
bom = pd.DataFrame(bom_rows, columns=[
    "ProductID", "ComponentID", "ComponentName", "ComponentUoM", "QtyPerUnit", "MapsToCostField",
])
bom.to_csv(OUT / "Bridge_BOM.csv", index=False)
print(f"BOM rows: {len(bom)}; product VC check OK")

# ---------- DimBOMComponent + FactBOMUsage (v1.9.0) ----------
# Canonical component dim; period×product usage rolls money from DimProduct cost fields
dim_bom_comp = pd.DataFrame([
    ("RAW-MILK", "Raw milk", "L", "Dairy Input", "RawMilkCost"),
    ("PACK-PRIMARY", "Primary pack (carton/cup/tub)", "EA", "Packaging", "PackagingCost"),
    ("PROC-ENERGY", "Processing energy / CIP proxy", "kWh-eq", "Utilities", "ProcessingEnergyCost"),
    ("OTHER-VAR", "Other variable (culture/aux/misc)", "LOT", "Other", "OtherVariableCost"),
], columns=["ComponentID", "ComponentName", "ComponentUoM", "Category", "MapsToCostField"])
dim_bom_comp.to_csv(OUT / "DimBOMComponent.csv", index=False)

# Periods are built later; FactBOMUsage written after periods exist (see end of financial section)

# ---------- DimLine ----------
pd.DataFrame([
    ("L1", "Filler A - Fresh milk (high speed)", "Fresh Hall", "Dedicated"),
    ("L2", "Filler B - Fresh / drinkable yogurt", "Fresh Hall", "Flexible"),
    ("L3", "Cup line - Yogurt & cultured", "Cultured Hall", "Dedicated"),
    ("L4", "Pack line - Cheese & butter", "Pack Hall", "Flexible"),
], columns=["LineID", "LineName", "ProductionArea", "CapacityType"]).to_csv(
    OUT / "DimLine.csv", index=False
)

# ---------- DimEquipment ----------
eq = []
eq.append(("EQ-L1", "Pasteurizer / Homogenizer A", "L1", "Pasteurizer"))
eq.append(("EQ-L1-F", "Carton filler A", "L1", "Filler"))
eq.append(("EQ-L2", "Pasteurizer B", "L2", "Pasteurizer"))
eq.append(("EQ-L2-F", "Carton / bottle filler B", "L2", "Filler"))
eq.append(("EQ-L3", "Fermentation tanks", "L3", "Process"))
eq.append(("EQ-L3-F", "Cup filler / sealer", "L3", "Filler"))
# L4 equipment referenced if downtime hits L4 via random — keep a pair
eq.append(("EQ-L4", "Block cutter / wrapper", "L4", "Packaging"))
eq.append(("EQ-L4-F", "Case packer", "L4", "Packaging"))
pd.DataFrame(eq, columns=["EquipmentID", "EquipmentName", "LineID", "EquipmentType"]).to_csv(
    OUT / "DimEquipment.csv", index=False
)

# ---------- Bridge ----------
bridge = pd.DataFrame([
    ("P1", "L1", 120, 1.0), ("P1", "L2", 90, 2.0),
    ("P2", "L1", 140, 1.0),
    ("P3", "L2", 100, 1.0), ("P3", "L1", 70, 2.5),
    ("P4", "L3", 200, 1.0), ("P4", "L4", 150, 2.0),
    ("P5", "L3", 180, 1.0), ("P5", "L4", 130, 2.0),
    ("P6", "L2", 110, 1.0),
    ("P7", "L3", 60, 1.0), ("P7", "L4", 45, 2.0),
    ("P8", "L2", 55, 1.0),
], columns=["ProductID", "LineID", "StandardRate", "SetupTime_h"])
bridge["ValidFrom"] = "2024-01-01"
bridge["ValidTo"] = "9999-12-31"
bridge.to_csv(OUT / "Bridge_ProductLineCapability.csv", index=False)

prim_line = {p: g.iloc[0].LineID for p, g in bridge.groupby("ProductID", sort=True)}
prim_rate = {p: g.iloc[0].StandardRate for p, g in bridge.groupby("ProductID", sort=True)}

# ---------- DimDowntimeReason ----------
pd.DataFrame([
    ("D1", "Raw milk / ingredient shortage", "Material", "Unplanned", "Availability"),
    ("D2", "Filler / pasteurizer breakdown", "Equipment", "Unplanned", "Availability"),
    ("D3", "Utilities fault (steam/power/cooling)", "Equipment", "Unplanned", "Availability"),
    ("D4", "Planned maintenance", "Planned", "Planned", "Availability"),
    ("D5", "CIP / sanitation", "Planned", "Planned", "Availability"),
    ("D6", "SKU changeover (allergen / pack size)", "Planned", "Planned", "Availability"),
    ("D7", "Micro-stops / speed loss on filler", "Process", "Unplanned", "Performance"),
    ("D8", "Quality hold / lab reject", "Quality", "Unplanned", "Quality"),
], columns=["DowntimeReasonID", "Reason", "Category", "PlannedUnplanned", "LossType"]).to_csv(
    OUT / "DimDowntimeReason.csv", index=False
)

# ---------- DimScenario ----------
# NOTE: Original had typo "S3S5". No valid business definition existed.
# Kept as separate S3 (+3pt) and S5 (+5pt). Documented in DATA_DICTIONARY.md.
pd.DataFrame([
    ("S0", "Baseline", "Baseline", "As-run baseline"),
    ("S1", "OEE +1pt", "Operational", "Performance +1 percentage point"),
    ("S3", "OEE +3pt", "Operational", "Performance +3 percentage points"),
    ("S5", "OEE +5pt", "Operational", "Performance +5 percentage points"),
    ("SD10", "Downtime -10%", "Operational", "Unplanned downtime reduced 10% (~+2% output)"),
    ("SQ", "Scrap -30%", "Operational", "Quality improvement: 30% of scrap recovered"),
    ("SDP", "Demand +10%", "Demand", "Firm demand +10%"),
    ("SR", "Recovery +50%", "Recovery", "Recovery capacity +50%"),
], columns=["ScenarioID", "ScenarioName", "ScenarioType", "Description"]).to_csv(
    OUT / "DimScenario.csv", index=False
)

# ---------- ScenarioParameters (config table; engine reads this) ----------
pd.DataFrame([
    dict(ScenarioID="S0", ScenarioName="Baseline", ScenarioType="Baseline",
         OEE_Uplift_pts=0.0, Output_Factor=1.0, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="As-run baseline"),
    dict(ScenarioID="S1", ScenarioName="OEE +1pt", ScenarioType="Operational",
         OEE_Uplift_pts=0.01, Output_Factor=1.0, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Performance +1 percentage point"),
    dict(ScenarioID="S3", ScenarioName="OEE +3pt", ScenarioType="Operational",
         OEE_Uplift_pts=0.03, Output_Factor=1.0, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Performance +3 percentage points"),
    dict(ScenarioID="S5", ScenarioName="OEE +5pt", ScenarioType="Operational",
         OEE_Uplift_pts=0.05, Output_Factor=1.0, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Performance +5 percentage points"),
    dict(ScenarioID="SD10", ScenarioName="Downtime -10%", ScenarioType="Operational",
         OEE_Uplift_pts=0.0, Output_Factor=1.02, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Unplanned downtime -10% (~+2% output)"),
    dict(ScenarioID="SQ", ScenarioName="Scrap -30%", ScenarioType="Operational",
         OEE_Uplift_pts=0.0, Output_Factor=1.0, Scrap_Recover_Frac=0.30,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Quality: 30% of scrap recovered as good"),
    dict(ScenarioID="SDP", ScenarioName="Demand +10%", ScenarioType="Demand",
         OEE_Uplift_pts=0.0, Output_Factor=1.0, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.10, Recovery_Frac_Mult=1.0, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Firm demand +10%"),
    dict(ScenarioID="SR", ScenarioName="Recovery +50%", ScenarioType="Recovery",
         OEE_Uplift_pts=0.0, Output_Factor=1.0, Scrap_Recover_Frac=0.0,
         Demand_Factor=1.0, Recovery_Frac_Mult=1.50, Price_Factor=1.0, Cost_Factor=1.0,
         Description="Recovery capacity +50%"),
]).to_csv(OUT / "ScenarioParameters.csv", index=False)

# ---------- ModelAssumptions (versioned operational/finance config) ----------
pd.DataFrame([
    dict(Parameter="RECOVERY_FRAC", Value=0.20, Unit="fraction",
         Description="Fraction of remaining gap recoverable under baseline"),
    dict(Parameter="RECOVERY_COST_UNIT", Value=8.0, Unit="USD/EA",
         Description="Variable cost of recovery or substitution per unit"),
    dict(Parameter="BOTTLENECK_THRESH", Value=0.95, Unit="ratio",
         Description="Line utilization threshold for bottleneck flag"),
    dict(Parameter="CURRENCY", Value="USD", Unit="",
         Description="Reporting currency"),
    dict(Parameter="VOLUME_UNIT", Value="EA", Unit="",
         Description="Volume unit: retail packs (EA); see DimProduct.LitersPerUnit for dairy liters"),
    dict(Parameter="SAME_PERIOD_SHIP", Value=1, Unit="boolean",
         Description="1=production can ship in same period; 0=only opening inventory can ship"),
    dict(Parameter="PRIMARY_LINE_RULE", Value="PRIMARY_ALLOCATED", Unit="",
         Description="Impact LineID = primary capable line per product (not multi-line grain)"),
    dict(Parameter="HOLDING_COST_ANNUAL_WACC", Value=0.18, Unit="fraction",
         Description="Annual inventory holding rate (WACC+storage proxy); applied monthly as /12"),
    dict(Parameter="RECOVERY_COST_MODE", Value="STEPPED", Unit="",
         Description="FLAT uses RECOVERY_COST_UNIT; STEPPED uses tier costs below"),
    dict(Parameter="RECOVERY_TIER1_FRAC", Value=0.05, Unit="fraction of gap",
         Description="First slice of mitigated units priced at TIER1 cost"),
    dict(Parameter="RECOVERY_TIER1_COST", Value=2.0, Unit="USD/EA",
         Description="Line speed / minor recovery cost"),
    dict(Parameter="RECOVERY_TIER2_FRAC", Value=0.15, Unit="fraction of gap",
         Description="Cumulative through this frac at TIER2 cost for middle band"),
    dict(Parameter="RECOVERY_TIER2_COST", Value=7.0, Unit="USD/EA",
         Description="1.5x overtime-style recovery cost"),
    dict(Parameter="RECOVERY_TIER3_COST", Value=14.0, Unit="USD/EA",
         Description="Weekend / co-pack style recovery cost for remainder"),
    dict(Parameter="P_REALIZE", Value=0.65, Unit="fraction",
         Description="Assumed probability that modeled Net CM opportunity is realized; for risk-adjusted benefit"),
]).to_csv(OUT / "ModelAssumptions.csv", index=False)

# Runtime flag — read back from the file just written (single source of truth)
_ass = pd.read_csv(OUT / "ModelAssumptions.csv")
_ass_map = dict(zip(_ass.Parameter.astype(str), _ass.Value))
SAME_PERIOD_SHIP = int(float(_ass_map["SAME_PERIOD_SHIP"]))
if SAME_PERIOD_SHIP not in (0, 1):
    raise ValueError(f"SAME_PERIOD_SHIP must be 0 or 1, got {SAME_PERIOD_SHIP}")
print(f"SAME_PERIOD_SHIP={SAME_PERIOD_SHIP} (from ModelAssumptions.csv)")

# ---------- FactProduction ----------
rows = []
for p in prim_line:
    for d in dates:
        if d.weekday() >= 5 and rng.random() < 0.7:
            continue
        if rng.random() < 0.12:
            continue
        ptt = rng.choice([8, 12, 16], p=[0.3, 0.4, 0.3])
        dtm = min(ptt * 60 * 0.5, rng.gamma(2.0, 15))
        co = rng.choice([0, 30, 45, 60], p=[0.4, 0.25, 0.2, 0.15])
        run = (ptt * 60 - dtm - co) / 60.0
        rate = prim_rate[p]
        ideal = 1.0 / rate
        total = run * rate * rng.uniform(0.90, 0.99)
        scrap_r = rng.uniform(0.01, 0.05) + (0.03 if p in ("P3", "P6") else 0)
        scrap = total * scrap_r
        good = total - scrap
        rework = good * rng.uniform(0.005, 0.02)
        rows.append((
            f"PR{len(rows)+1:05d}", d.strftime("%Y%m%d"), p, prim_line[p],
            ptt, round(run, 3), round(ideal, 6),
            int(round(good)), int(round(scrap)), int(round(rework)), co,
            int(round(good + scrap + rework)),
        ))
fp = pd.DataFrame(rows, columns=[
    "ProductionRunID", "DateKey", "ProductID", "LineID",
    "PlannedProductionTime_h", "RunTime_h", "StandardCycleTime_h",
    "GoodUnits", "ScrapUnits", "ReworkUnits", "ChangeoverTime_min", "TotalUnits",
])
fp.to_csv(OUT / "FactProduction.csv", index=False)

# ---------- FactDowntime ----------
dr = []
k = 0
for _, r in fp.iterrows():
    if rng.random() < 0.45:
        k += 1
        dur = max(5, min(r.PlannedProductionTime_h * 60 - r.ChangeoverTime_min, rng.gamma(2, 12)))
        dr.append((
            f"DT{k:05d}", r.DateKey,
            (f"EQ-{r.LineID}-F" if rng.random() < 0.45 else f"EQ-{r.LineID}"),
            r.LineID, int(round(dur)),
            rng.choice(["D1", "D2", "D3", "D6", "D7", "D8"]),
            "Unplanned" if rng.random() < 0.85 else "Planned",
        ))
pd.DataFrame(dr, columns=[
    "DowntimeEventID", "DateKey", "EquipmentID", "LineID",
    "DurationMinutes", "DowntimeReasonID", "PlannedUnplanned",
]).to_csv(OUT / "FactDowntime.csv", index=False)

# ---------- Monthly production aggregate ----------
fp["MonthKey"] = fp.DateKey.str[:6]
mp = fp.groupby(["MonthKey", "ProductID"]).GoodUnits.sum().reset_index()
mp = mp.rename(columns={"GoodUnits": "GoodProduction"})

# ---------- Demand targets (calibrated shortfalls) ----------
season = {1: 0.92, 2: 0.90, 3: 1.02, 4: 1.00, 5: 0.98, 6: 1.05,
          7: 1.10, 8: 1.12, 9: 1.08, 10: 1.02, 11: 0.95, 12: 0.96}
fulfill_target = {
    "P1": 1.12, "P2": 1.00, "P3": 1.15, "P4": 0.82,
    "P5": 0.92, "P6": 1.08, "P7": 0.88, "P8": 1.03,
}

# ---------- Inventory roll-forward + Demand + Sales ----------
# Grain: ProductID x PeriodKey (YYYYMM)
# Closing = Opening + GoodProduction - Shipments
# Opening(t+1) = Closing(t)
# Shipments = min(FirmDemand, Opening + GoodProduction) if SAME_PERIOD_SHIP else min(FirmDemand, Opening)
# Initial opening: modest safety stock (~3-6% of first month production)

periods = sorted(mp.MonthKey.unique())
products = sorted(prim_line.keys())

dem_rows = []
inv_rows = []  # product x period roll-forward (pre-location split)
sales_meta = []  # MonthKey, ProductID, Shipments for sales split

# Seed initial opening per product
initial_opening = {}
for p in products:
    first = mp[(mp.MonthKey == periods[0]) & (mp.ProductID == p)]
    g0 = float(first.GoodProduction.iloc[0]) if len(first) else 1000.0
    initial_opening[p] = int(round(g0 * rng.uniform(0.03, 0.07)))

opening = dict(initial_opening)

for period in periods:
    m = int(period[4:6])
    for p in products:
        gp_row = mp[(mp.MonthKey == period) & (mp.ProductID == p)]
        good_prod = int(gp_row.GoodProduction.iloc[0]) if len(gp_row) else 0

        target = fulfill_target[p] * season[m] * rng.uniform(0.94, 1.06)
        # Firm demand calibrated vs production (same spirit as original)
        firm = max(0, int(round(good_prod * target)))
        expected = max(firm, int(round(firm * rng.uniform(1.02, 1.10))))

        dem_rows.append((period, p, "Firm", "S0", firm))
        dem_rows.append((period, p, "Expected", "S0", expected))

        if SAME_PERIOD_SHIP:
            avail = opening[p] + good_prod  # production available to ship same period
        else:
            avail = opening[p]  # only opening stock ships; production lands in closing
        shipments = min(firm, avail)
        closing = opening[p] + good_prod - shipments

        assert closing >= 0, f"Negative closing {p} {period}"
        inv_rows.append({
            "PeriodKey": period,
            "ProductID": p,
            "OpeningInventory": opening[p],
            "GoodProduction": good_prod,
            "Shipments": shipments,
            "ClosingInventory": closing,
            "FirmDemand": firm,
        })
        sales_meta.append((period, p, shipments, firm))
        opening[p] = closing  # roll forward

fod = pd.DataFrame(dem_rows, columns=["PeriodKey", "ProductID", "DemandType", "ScenarioID", "DemandUnits"])
fod.to_csv(OUT / "FactDemand.csv", index=False)

inv_pf = pd.DataFrame(inv_rows)

# Mass-balance check
inv_pf["ExpectedClosing"] = inv_pf.OpeningInventory + inv_pf.GoodProduction - inv_pf.Shipments
bal_err = (inv_pf.ClosingInventory - inv_pf.ExpectedClosing).abs().max()
assert bal_err <= 0, f"Mass balance error max={bal_err}"

# Continuity check
inv_pf = inv_pf.sort_values(["ProductID", "PeriodKey"])
inv_pf["PrevClosing"] = inv_pf.groupby("ProductID")["ClosingInventory"].shift(1)
cont = inv_pf[inv_pf.PrevClosing.notna()]
cont_err = (cont.OpeningInventory - cont.PrevClosing).abs().max()
assert cont_err <= 0, f"Continuity error max={cont_err}"

print(f"Inventory mass-balance max error: {bal_err}")
print(f"Inventory continuity max error: {cont_err}")

nshort = int((inv_pf.FirmDemand > inv_pf.Shipments).sum())
print(f"product-months short of firm demand: {nshort} of {len(inv_pf)} "
      f"| shortfall share: {100 * nshort / len(inv_pf):.1f}%")
print(f"total shortfall units: {int((inv_pf.FirmDemand - inv_pf.Shipments).clip(lower=0).sum())}")

# ---------- FactInventorySnapshot (location split of closing FG) ----------
# Business rule: FG at period end = ClosingInventory, split across warehouses.
# UsableInventory = FG_final - Blocked_final (from final rounded values).
inv_snap = []
for _, r in inv_pf.iterrows():
    closing = int(r.ClosingInventory)
    # Split closing FG across two locations (Central gets more)
    share_c = rng.uniform(0.55, 0.70)
    fg_c_raw = closing * share_c
    fg_e_raw = closing - fg_c_raw

    for loc, fg_raw in [("CS-MAIN", fg_c_raw), ("CS-DISPATCH", fg_e_raw)]:
        blocked_raw = fg_raw * rng.uniform(0, 0.12)
        safety_raw = fg_raw * rng.uniform(0.08, 0.20)

        fg_final = int(round(fg_raw))
        blocked_final = int(round(blocked_raw))
        # Enforce blocked <= fg
        blocked_final = min(blocked_final, fg_final)
        safety_final = int(round(safety_raw))
        safety_final = min(safety_final, max(0, fg_final - blocked_final))

        usable_final = fg_final - blocked_final
        assert usable_final == fg_final - blocked_final
        assert usable_final >= 0
        assert blocked_final >= 0
        assert fg_final >= 0

        absorbable = max(0, usable_final - safety_final)

        inv_snap.append((
            r.PeriodKey, r.ProductID, loc,
            fg_final, blocked_final, safety_final, usable_final, 0,
            absorbable,
            int(r.OpeningInventory), int(r.OpeningInventory), int(r.GoodProduction), int(r.Shipments), int(r.ClosingInventory),
        ))

fiv = pd.DataFrame(inv_snap, columns=[
    "PeriodKey", "ProductID", "LocationID",
    "FGInventory", "BlockedInventory", "SafetyStock", "UsableInventory", "WIP",
    "AbsorbableInventory",
    "OpeningInventory", "OpeningAvailableInventory", "GoodProduction", "Shipments", "ClosingInventory",
])
# Final rounding consistency assertion
assert (fiv.UsableInventory == fiv.FGInventory - fiv.BlockedInventory).all(), \
    "UsableInventory rounding inconsistency"
fiv.to_csv(OUT / "FactInventorySnapshot.csv", index=False)

# ---------- DimPeriod (monthly calendar for period-grain facts) ----------
periods = sorted(fiv.PeriodKey.astype(str).unique())
pd.DataFrame({
    "PeriodKey": periods,
    "Year": [int(x[:4]) for x in periods],
    "Month": [int(x[4:6]) for x in periods],
    "FiscalPeriod": periods,
}).to_csv(OUT / "DimPeriod.csv", index=False)

# ---------- DimLocation ----------
pd.DataFrame({
    "LocationID": ["CS-MAIN", "CS-DISPATCH"],
    "LocationName": ["Main cold store (0-4C)", "Dispatch cold dock"],
    "LocationType": ["ColdStore", "ColdStore"],
}).to_csv(OUT / "DimLocation.csv", index=False)

# ---------- FactSales from roll-forward shipments ----------
t = 0
sales = []
for period, p, ship, firm in sales_meta:
    if ship <= 0:
        continue
    ntx = int(rng.integers(2, 5))
    # Multinomial allocation produces integer transaction units whose total equals
    # shipments exactly; independent rounding of Dirichlet allocations created drift.
    probs = rng.dirichlet(np.ones(ntx))
    alloc = rng.multinomial(int(ship), probs)
    price_f = rng.uniform(0.97, 1.0)
    for units in alloc:
        if units <= 0:
            continue
        t += 1
        gross = units * sp.StandardPrice[p] * price_f
        disc = gross * rng.uniform(0.02, 0.06)
        ret = gross * rng.uniform(0, 0.02)
        allow = gross * rng.uniform(0, 0.01)
        net = gross - disc - ret - allow
        vc = units * sp.StandardVariableCost[p]
        sales.append((
            f"ST{t:05d}", period + "15", p, units,
            round(gross, 2), round(disc, 2), round(ret, 2), round(allow, 2),
            round(net, 2), round(vc, 2),
        ))

fs = pd.DataFrame(sales, columns=[
    "SalesTransactionID", "DateKey", "ProductID", "Units",
    "GrossRevenue", "Discount", "Returns", "Allowances",
    "NetRevenue", "VariableCost",
])
fs["CM"] = (fs.NetRevenue - fs.VariableCost).round(2)
fs.to_csv(OUT / "FactSales.csv", index=False)

# Sales <= FirmDemand and Sales <= Opening+Good
ms = fs.copy()
ms["PeriodKey"] = ms.DateKey.str[:6]
ms = ms.groupby(["PeriodKey", "ProductID"], as_index=False)["Units"].sum()
chk = ms.merge(
    inv_pf[["PeriodKey", "ProductID", "FirmDemand", "OpeningInventory", "GoodProduction", "Shipments"]],
    on=["PeriodKey", "ProductID"], how="left",
)
assert (chk.Units <= chk.FirmDemand).all(), "Sales > FirmDemand"
if SAME_PERIOD_SHIP:
    assert (chk.Units <= chk.OpeningInventory + chk.GoodProduction).all(), "Sales > available supply"
else:
    assert (chk.Units <= chk.OpeningInventory).all(), "Sales > opening when SAME_PERIOD_SHIP=0"
# Sales must reconcile exactly to the inventory roll-forward shipments.
ship_chk = chk.merge(
    inv_pf[["PeriodKey", "ProductID", "Shipments"]],
    on=["PeriodKey", "ProductID"], suffixes=("", "_rf"),
)
ship_err = (ship_chk.Units - ship_chk.Shipments).abs()
assert ship_err.max() == 0, \
    f"Sales vs Shipments mismatch: max diff={ship_err.max()}"

# ---------- FactFinancialPlan ----------
fin = []
for p in products:
    for period in periods:
        exp = fod[
            (fod.PeriodKey == period) & (fod.ProductID == p) & (fod.DemandType == "Expected")
        ].DemandUnits.iloc[0]
        bv = int(round(exp * 0.98))
        fin.append((
            period, p, "S0",
            bv, round(bv * sp.StandardPrice[p], 2), sp.StandardPrice[p],
            round(bv * sp.StandardCM[p], 2),
            int(exp), round(exp * sp.StandardPrice[p], 2),
            round(exp * sp.StandardCM[p], 2),
        ))
pd.DataFrame(fin, columns=[
    "PeriodKey", "ProductID", "ScenarioID",
    "BudgetVolume", "BudgetRevenue", "BudgetPrice", "BudgetCM",
    "ForecastVolume", "ForecastRevenue", "ForecastCM",
]).to_csv(OUT / "FactFinancialPlan.csv", index=False)


# ---------- FactBOMUsage (v1.9.0): Product × Period × Component ----------
bom_usage_rows = []
cost_map = {
    "RAW-MILK": "RawMilkCost",
    "PACK-PRIMARY": "PackagingCost",
    "PROC-ENERGY": "ProcessingEnergyCost",
    "OTHER-VAR": "OtherVariableCost",
}
for p in products:
    for period in periods:
        for comp_id, field in cost_map.items():
            bom_usage_rows.append({
                "PeriodKey": period,
                "ProductID": p,
                "ComponentID": comp_id,
                "BudgetQtyPerUnit": 1.0,
                "StdCostPerUnit": float(sp[field][p]),
            })
pd.DataFrame(bom_usage_rows).to_csv(OUT / "FactBOMUsage.csv", index=False)

# ---------- FactCOGSVariance (v1.9.0) ----------
# BudgetCOGS = BudgetVolume × StandardVariableCost
# YieldVariance = (Scrap + Rework) × StandardVariableCost  (unfavorable quality loss at std cost)
# ActualCOGS = GoodUnits × VC + YieldVariance = (Good+Scrap+Rework) × VC at standard
fp_m = fp.copy()
fp_m["PeriodKey"] = pd.to_datetime(fp_m["DateKey"].astype(str), format="%Y%m%d").dt.strftime("%Y%m")
prod_m = fp_m.groupby(["PeriodKey", "ProductID"], as_index=False).agg(
    GoodUnits=("GoodUnits", "sum"),
    ScrapUnits=("ScrapUnits", "sum"),
    ReworkUnits=("ReworkUnits", "sum"),
)
fin_df = pd.read_csv(OUT / "FactFinancialPlan.csv")
fin_s0 = fin_df[fin_df["ScenarioID"] == "S0"][["PeriodKey", "ProductID", "BudgetVolume"]].copy()
fin_s0["PeriodKey"] = fin_s0["PeriodKey"].astype(str)
fin_s0["ProductID"] = fin_s0["ProductID"].astype(str)
prod_m["PeriodKey"] = prod_m["PeriodKey"].astype(str)
prod_m["ProductID"] = prod_m["ProductID"].astype(str)
cogs_rows = []
for _, r in fin_s0.iterrows():
    pk, pid = str(r.PeriodKey), str(r.ProductID)
    vc = float(sp.StandardVariableCost[pid])
    bv = float(r.BudgetVolume)
    sub = prod_m[(prod_m.PeriodKey == pk) & (prod_m.ProductID == pid)]
    good = float(sub.GoodUnits.sum()) if len(sub) else 0.0
    scrap = float(sub.ScrapUnits.sum()) if len(sub) else 0.0
    rework = float(sub.ReworkUnits.sum()) if len(sub) else 0.0
    yield_var = (scrap + rework) * vc
    budget_cogs = bv * vc
    actual_cogs = good * vc + yield_var
    cogs_rows.append({
        "PeriodKey": pk,
        "ProductID": pid,
        "BudgetVolume": bv,
        "GoodUnits": good,
        "ScrapUnits": scrap,
        "ReworkUnits": rework,
        "StandardVariableCost": vc,
        "BudgetCOGS": round(budget_cogs, 2),
        "YieldVariance": round(yield_var, 2),
        "ActualCOGS": round(actual_cogs, 2),
        "VolumeCOGSEffect": round((good - bv) * vc, 2),
    })
fact_cogs = pd.DataFrame(cogs_rows)
# Identity: BudgetCOGS + VolumeCOGSEffect + YieldVariance ≈ ActualCOGS
_cogs_err = (fact_cogs.BudgetCOGS + fact_cogs.VolumeCOGSEffect + fact_cogs.YieldVariance - fact_cogs.ActualCOGS).abs().max()
assert _cogs_err < 0.05, f"COGS identity fail max_err={_cogs_err}"
fact_cogs.to_csv(OUT / "FactCOGSVariance.csv", index=False)
print(f"FactBOMUsage rows={len(bom_usage_rows)}; FactCOGSVariance rows={len(fact_cogs)}; COGS identity max_err={_cogs_err}")

# ---------- Summary ----------
print("Rows: prod %d, downtime %d, sales %d, inv_snap %d, demand %d, plan %d" % (
    len(fp), len(dr), len(fs), len(fiv), len(fod), len(fin),
))
assert ((fp.GoodUnits <= fp.TotalUnits) & (fp.ScrapUnits <= fp.TotalUnits)).all()
print("Integrity checks passed.")
print(f"Output written to {OUT}")
