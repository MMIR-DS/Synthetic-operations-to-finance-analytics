# Data Model — OEE → Revenue → CM (v1.9.0)

Domain skin: **imaginary dairy factory**. Kimball star schema + bridge + derived facts.

## Hybrid integrity

| Layer | Mechanism |
|-------|-----------|
| Python | Business rules → `final/integrity_checks.json` (24/24) |
| SQLite | PK/FK via `05_build_sqlite_with_keys.py`, `PRAGMA foreign_keys=ON` |

## Dimensions

DimDate, DimPeriod, DimProduct, DimLine, DimEquipment, DimDowntimeReason, DimScenario, DimLocation, DimBOMComponent

## Bridge

`Bridge_ProductLineCapability` (ProductID × LineID)

## Base facts

| Table | Grain | Time |
|-------|-------|------|
| FactProduction | run | DateKey |
| FactDowntime | event | DateKey |
| FactSales | transaction | DateKey |
| FactDemand | Product×Period×Scenario×DemandType | PeriodKey |
| FactFinancialPlan | Product×Period×Scenario | PeriodKey |
| FactInventorySnapshot | Product×Period×Location | PeriodKey |
| FactBOMUsage | Product×Period×Component | PeriodKey |
| FactCOGSVariance | Product×Period | PeriodKey |

## Derived facts

| Table | Grain |
|-------|-------|
| FactOEE_Run | 1:1 with production run |
| FactImpact_ProductPeriod | PeriodKey × ProductID (LineID attribute) |

## Inventory note

Flow columns (Opening/Good/Ship/Closing) are Product×Period — **do not SUM by Location**.

## Shipping rule

- `SAME_PERIOD_SHIP=1`: ship ≤ opening + good production
- `SAME_PERIOD_SHIP=0`: ship ≤ opening only

## Metric hierarchy

1. Net CM opportunity = ProtectedCM − RecoveryCost
2. Net after incremental holding (proxy)
3. Net after total FG holding (context only)

All **Modeled / assumption-driven / not a forecast**.
