"""Build oee_revenue_cm_model.db with PKs, FKs, DimPeriod, DimLocation (v1.5 data model)."""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT, FIN = ROOT / "output", ROOT / "final"
TMP = Path("/tmp/oee_revenue_cm_model_v15.db")
DB = FIN / "oee_revenue_cm_model.db"


def S(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str)
    return df


def main():
    DimDate = S(pd.read_csv(OUT / "DimDate.csv"), ["DateKey"])
    DimPeriod = S(pd.read_csv(OUT / "DimPeriod.csv"), ["PeriodKey"])
    DimProduct = S(pd.read_csv(OUT / "DimProduct.csv"), ["ProductID"])
    DimLine = S(pd.read_csv(OUT / "DimLine.csv"), ["LineID"])
    DimEquipment = S(pd.read_csv(OUT / "DimEquipment.csv"), ["EquipmentID", "LineID"])
    DimReason = S(pd.read_csv(OUT / "DimDowntimeReason.csv"), ["DowntimeReasonID"])
    DimScenario = S(pd.read_csv(OUT / "DimScenario.csv"), ["ScenarioID"])
    DimLocation = S(pd.read_csv(OUT / "DimLocation.csv"), ["LocationID"])
    Bridge = S(pd.read_csv(OUT / "Bridge_ProductLineCapability.csv"), ["ProductID", "LineID"])
    FactProduction = S(pd.read_csv(OUT / "FactProduction.csv"), ["ProductionRunID", "DateKey", "ProductID", "LineID"])
    FactDowntime = S(pd.read_csv(OUT / "FactDowntime.csv"), ["DowntimeEventID", "DateKey", "EquipmentID", "LineID", "DowntimeReasonID"])
    FactSales = S(pd.read_csv(OUT / "FactSales.csv"), ["SalesTransactionID", "DateKey", "ProductID"])
    FactDemand = S(pd.read_csv(OUT / "FactDemand.csv"), ["PeriodKey", "ProductID", "DemandType", "ScenarioID"])
    FactInv = S(pd.read_csv(OUT / "FactInventorySnapshot.csv"), ["PeriodKey", "ProductID", "LocationID"])
    FactPlan = S(pd.read_csv(OUT / "FactFinancialPlan.csv"), ["PeriodKey", "ProductID", "ScenarioID"])
    ModelAssumptions = pd.read_csv(OUT / "ModelAssumptions.csv")
    ScenParams = S(pd.read_csv(OUT / "ScenarioParameters.csv"), ["ScenarioID"])
    FactOEE = S(pd.read_csv(FIN / "FactOEE_Run.csv"), ["ProductionRunID", "DateKey", "ProductID", "LineID"])
    Impact = S(pd.read_csv(FIN / "FactImpact_ProductPeriod.csv"), ["PeriodKey", "ProductID", "LineID"])
    PVM = S(pd.read_csv(FIN / "PVM_Bridge.csv"), ["PeriodKey", "ProductID"])
    ScenRes = S(pd.read_csv(FIN / "Scenario_Results.csv"), ["ScenarioID"])
    Opp = S(pd.read_csv(FIN / "Opportunity_Prioritization.csv"), ["PeriodKey", "ProductID"])
    CaseTrace = S(pd.read_csv(FIN / "CaseTrace.csv"), ["PeriodKey", "ProductID", "LineID"])
    DimBOMComponent = S(pd.read_csv(OUT / "DimBOMComponent.csv"), ["ComponentID"])
    FactBOMUsage = S(pd.read_csv(OUT / "FactBOMUsage.csv"), ["PeriodKey", "ProductID", "ComponentID"])
    FactCOGSVariance = S(pd.read_csv(OUT / "FactCOGSVariance.csv"), ["PeriodKey", "ProductID"])
    PLBridge = S(pd.read_csv(FIN / "PL_Bridge_Summary.csv"), ["PeriodKey"]) if (FIN / "PL_Bridge_Summary.csv").exists() else None

    if "Description" not in DimScenario.columns:
        DimScenario["Description"] = DimScenario.get("ScenarioName", "")

    if TMP.exists():
        TMP.unlink()
    con = sqlite3.connect(str(TMP))
    con.execute("PRAGMA foreign_keys = ON")

    ddls = [
        "CREATE TABLE DimDate (DateKey TEXT PRIMARY KEY, Date TEXT, Month INTEGER, Year INTEGER, Quarter TEXT, FiscalPeriod TEXT, FiscalYear TEXT)",
        "CREATE TABLE DimPeriod (PeriodKey TEXT PRIMARY KEY, Year INTEGER, Month INTEGER, FiscalPeriod TEXT)",
        "CREATE TABLE DimProduct (ProductID TEXT PRIMARY KEY, ProductName TEXT, ProductFamily TEXT, ProductCategory TEXT, UnitOfMeasure TEXT, StandardPrice REAL, StandardVariableCost REAL, StandardCM REAL)",
        "CREATE TABLE DimLine (LineID TEXT PRIMARY KEY, LineName TEXT, ProductionArea TEXT, CapacityType TEXT)",
        "CREATE TABLE DimEquipment (EquipmentID TEXT PRIMARY KEY, EquipmentName TEXT, LineID TEXT NOT NULL, EquipmentType TEXT, FOREIGN KEY (LineID) REFERENCES DimLine(LineID))",
        "CREATE TABLE DimDowntimeReason (DowntimeReasonID TEXT PRIMARY KEY, Reason TEXT, Category TEXT, PlannedUnplanned TEXT, LossType TEXT)",
        "CREATE TABLE DimScenario (ScenarioID TEXT PRIMARY KEY, ScenarioName TEXT, ScenarioType TEXT, Description TEXT)",
        "CREATE TABLE DimLocation (LocationID TEXT PRIMARY KEY, LocationName TEXT, LocationType TEXT)",
        """CREATE TABLE Bridge_ProductLineCapability (
            ProductID TEXT NOT NULL, LineID TEXT NOT NULL, StandardRate REAL, SetupTime_h REAL, ValidFrom TEXT, ValidTo TEXT,
            PRIMARY KEY (ProductID, LineID),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (LineID) REFERENCES DimLine(LineID))""",
        "CREATE TABLE ModelAssumptions (Parameter TEXT PRIMARY KEY, Value TEXT, Unit TEXT, Description TEXT)",
        """CREATE TABLE ScenarioParameters (
            ScenarioID TEXT PRIMARY KEY, ScenarioName TEXT, ScenarioType TEXT, OEE_Uplift_pts REAL, Output_Factor REAL,
            Scrap_Recover_Frac REAL, Demand_Factor REAL, Recovery_Frac_Mult REAL, Price_Factor REAL, Cost_Factor REAL, Description TEXT,
            FOREIGN KEY (ScenarioID) REFERENCES DimScenario(ScenarioID))""",
        """CREATE TABLE FactProduction (
            ProductionRunID TEXT PRIMARY KEY, DateKey TEXT NOT NULL, ProductID TEXT NOT NULL, LineID TEXT NOT NULL,
            PlannedProductionTime_h REAL, RunTime_h REAL, StandardCycleTime_h REAL, GoodUnits REAL, ScrapUnits REAL,
            ReworkUnits REAL, ChangeoverTime_min REAL, TotalUnits REAL,
            FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (LineID) REFERENCES DimLine(LineID))""",
        """CREATE TABLE FactDowntime (
            DowntimeEventID TEXT PRIMARY KEY, DateKey TEXT NOT NULL, EquipmentID TEXT NOT NULL, LineID TEXT NOT NULL,
            DurationMinutes REAL, DowntimeReasonID TEXT NOT NULL, PlannedUnplanned TEXT,
            FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
            FOREIGN KEY (EquipmentID) REFERENCES DimEquipment(EquipmentID),
            FOREIGN KEY (LineID) REFERENCES DimLine(LineID),
            FOREIGN KEY (DowntimeReasonID) REFERENCES DimDowntimeReason(DowntimeReasonID))""",
        """CREATE TABLE FactSales (
            SalesTransactionID TEXT PRIMARY KEY, DateKey TEXT NOT NULL, ProductID TEXT NOT NULL,
            Units REAL, GrossRevenue REAL, Discount REAL, Returns REAL, Allowances REAL, NetRevenue REAL, VariableCost REAL, CM REAL,
            FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID))""",
        """CREATE TABLE FactDemand (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL, DemandType TEXT NOT NULL, ScenarioID TEXT NOT NULL, DemandUnits REAL,
            PRIMARY KEY (PeriodKey, ProductID, DemandType, ScenarioID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (ScenarioID) REFERENCES DimScenario(ScenarioID))""",
        """CREATE TABLE FactInventorySnapshot (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL, LocationID TEXT NOT NULL,
            FGInventory REAL, BlockedInventory REAL, SafetyStock REAL, UsableInventory REAL, WIP REAL,
            AbsorbableInventory REAL, OpeningInventory REAL, OpeningAvailableInventory REAL, GoodProduction REAL, Shipments REAL, ClosingInventory REAL,
            PRIMARY KEY (PeriodKey, ProductID, LocationID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (LocationID) REFERENCES DimLocation(LocationID))""",
        """CREATE TABLE FactFinancialPlan (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL, ScenarioID TEXT NOT NULL,
            BudgetVolume REAL, BudgetRevenue REAL, BudgetCM REAL, ForecastVolume REAL, ForecastRevenue REAL, ForecastCM REAL,
            PRIMARY KEY (PeriodKey, ProductID, ScenarioID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (ScenarioID) REFERENCES DimScenario(ScenarioID))""",
        """CREATE TABLE FactOEE_Run (
            ProductionRunID TEXT PRIMARY KEY, DateKey TEXT, ProductID TEXT, LineID TEXT,
            PlannedProductionTime_h REAL, RunTime_h REAL, StandardCycleTime_h REAL, GoodUnits REAL, ScrapUnits REAL,
            ReworkUnits REAL, ChangeoverTime_min REAL, TotalUnits REAL, Availability REAL, Performance REAL, Quality REAL, OEE REAL,
            FOREIGN KEY (ProductionRunID) REFERENCES FactProduction(ProductionRunID),
            FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (LineID) REFERENCES DimLine(LineID))""",
        """CREATE TABLE FactImpact_ProductPeriod (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL, LineID TEXT,
            PlannedH REAL, RunH REAL, GoodUnits REAL, ScrapUnits REAL, OEE REAL, LineUtilization REAL, Bottleneck INTEGER,
            FirmDemand REAL, PrimarySupply REAL, OpeningAvailableInventory REAL, GrossGap REAL, InventoryAbsorbed REAL,
            RecoveredUnits REAL, SubstitutedUnits REAL, ResidualGap REAL, PotentialLostSalesUnits REAL,
            RevenueExposure REAL, CMExposure REAL, ProtectedCM REAL, RecoveryCost REAL, NetCMOpportunity REAL,
            AltLineID TEXT, AltRate REAL, CMUnit REAL, ExpNetPrice REAL,
            AvgInventory REAL, HoldingCost REAL, NetCM_after_Holding REAL,
            PRIMARY KEY (PeriodKey, ProductID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (LineID) REFERENCES DimLine(LineID))""",
        """CREATE TABLE PVM_Bridge (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL,
            AUnits REAL, ARev REAL, AVC REAL, BUnits REAL, BRev REAL, BCM REAL, BPrice REAL, ACM REAL,
            VolumeEffect REAL, MixEffect REAL, PriceEffect REAL, Residual REAL, ExpectedDelta REAL, CalculatedDelta REAL, PVMError REAL,
            PRIMARY KEY (PeriodKey, ProductID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID))""",
        """CREATE TABLE Scenario_Results (
            ScenarioID TEXT PRIMARY KEY, ScenarioName TEXT, ScenarioType TEXT, OEE_Uplift_pts REAL, Output_Factor REAL,
            Demand_Factor REAL, Recovery_Frac_Mult REAL, LostUnits_baseline REAL, LostUnits_scenario REAL,
            CMExposure_baseline REAL, CMExposure_scenario REAL, CMImpact REAL, RecoveryCost REAL, NetCMImpact_after_RecoveryCost REAL, Confidence TEXT,
            FOREIGN KEY (ScenarioID) REFERENCES DimScenario(ScenarioID))""",
        """CREATE TABLE Opportunity_Prioritization (
            PeriodKey TEXT, ProductID TEXT, LineID TEXT, GrossGap REAL, PotentialLostSalesUnits REAL, RevenueExposure REAL,
            CMExposure REAL, ProtectedCM REAL, RecoveryCost REAL, NetCMOpportunity REAL,
            TheoreticalCapacityGapUnits REAL, DemandConstrainedGapUnits REAL, ShipmentGapUnits REAL,
            RevenueOpportunity REAL, CMOpportunity REAL, RecoveryROI REAL, RecoveryROI_Status TEXT,
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID))""",
        
        """CREATE TABLE DimBOMComponent (
            ComponentID TEXT PRIMARY KEY, ComponentName TEXT, ComponentUoM TEXT, Category TEXT, MapsToCostField TEXT)""",
        """CREATE TABLE FactBOMUsage (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL, ComponentID TEXT NOT NULL,
            BudgetQtyPerUnit REAL, StdCostPerUnit REAL,
            PRIMARY KEY (PeriodKey, ProductID, ComponentID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID),
            FOREIGN KEY (ComponentID) REFERENCES DimBOMComponent(ComponentID))""",
        """CREATE TABLE FactCOGSVariance (
            PeriodKey TEXT NOT NULL, ProductID TEXT NOT NULL,
            BudgetVolume REAL, GoodUnits REAL, ScrapUnits REAL, ReworkUnits REAL, StandardVariableCost REAL,
            BudgetCOGS REAL, YieldVariance REAL, ActualCOGS REAL, VolumeCOGSEffect REAL,
            PRIMARY KEY (PeriodKey, ProductID),
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID))""",
        """CREATE TABLE PL_Bridge_Summary (
            PeriodKey TEXT PRIMARY KEY,
            BudgetRevenue REAL, VolumeEffect REAL, MixEffect REAL, PriceEffect REAL, ActualRevenue REAL,
            BudgetCOGS REAL, VolumeCOGSEffect REAL, YieldVariance REAL, ActualCOGS REAL,
            BudgetGP REAL, ActualGP REAL, GPVariance REAL,
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey))""",

        """CREATE TABLE CaseTrace (
            CaseType TEXT, PeriodKey TEXT, ProductID TEXT, LineID TEXT, OEE REAL, GoodUnits REAL, FirmDemand REAL,
            GrossGap REAL, InventoryAbsorbed REAL, RecoveredUnits REAL, SubstitutedUnits REAL, PotentialLostSalesUnits REAL,
            RevenueExposure REAL, CMExposure REAL, RecoveryCost REAL, NetCMOpportunity REAL, ManagementAction TEXT,
            FOREIGN KEY (PeriodKey) REFERENCES DimPeriod(PeriodKey),
            FOREIGN KEY (ProductID) REFERENCES DimProduct(ProductID))""",
    ]
    for d in ddls:
        con.execute(d)

    def ins(table: str, df: pd.DataFrame):
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        use = [c for c in cols if c in df.columns]
        df[use].to_sql(table, con, if_exists="append", index=False)

    for t, df in [
        ("DimDate", DimDate), ("DimPeriod", DimPeriod), ("DimProduct", DimProduct), ("DimLine", DimLine),
        ("DimEquipment", DimEquipment), ("DimDowntimeReason", DimReason), ("DimScenario", DimScenario),
        ("DimLocation", DimLocation), ("Bridge_ProductLineCapability", Bridge),
        ("ModelAssumptions", ModelAssumptions), ("ScenarioParameters", ScenParams),
        ("FactProduction", FactProduction), ("FactDowntime", FactDowntime), ("FactSales", FactSales),
        ("FactDemand", FactDemand), ("FactInventorySnapshot", FactInv), ("FactFinancialPlan", FactPlan),
        ("FactOEE_Run", FactOEE), ("FactImpact_ProductPeriod", Impact), ("PVM_Bridge", PVM),
        ("Scenario_Results", ScenRes), ("Opportunity_Prioritization", Opp), ("CaseTrace", CaseTrace),
        ("DimBOMComponent", DimBOMComponent), ("FactBOMUsage", FactBOMUsage),
        ("FactCOGSVariance", FactCOGSVariance),
    ]:
        ins(t, df)
    if PLBridge is not None:
        ins("PL_Bridge_Summary", PLBridge)

    con.execute("PRAGMA foreign_keys = ON")
    violations = []
    for t in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        rows = list(con.execute(f"PRAGMA foreign_key_check({t})"))
        if rows:
            violations.append((t, rows[:3]))

    orphan_ok = False
    try:
        con.execute(
            "INSERT INTO FactSales (SalesTransactionID, DateKey, ProductID, Units) VALUES (?,?,?,?)",
            ("ORPHAN", "20240101", "NOPE", 1),
        )
        con.commit()
    except sqlite3.IntegrityError:
        orphan_ok = True
        con.rollback()

    con.commit()
    report = [
        f"PRAGMA foreign_keys=ON, orphan_rejected={orphan_ok}, violations={len(violations)}",
        "PRIMARY KEYS:",
    ]
    for t in sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")):
        pk = [r[1] for r in con.execute(f"PRAGMA table_info({t})") if r[5]]
        report.append(f"  {t}: {pk or '(none)'}")
    report.append("FOREIGN KEYS:")
    for t in sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")):
        for fk in con.execute(f"PRAGMA foreign_key_list({t})"):
            report.append(f"  {t}.{fk[3]} -> {fk[2]}.{fk[4]}")
    con.close()
    shutil.copy2(TMP, DB)
    (FIN / "schema_keys_report.txt").write_text("\n".join(report))
    print("\n".join(report))
    print(f"DB -> {DB}")


if __name__ == "__main__":
    main()
