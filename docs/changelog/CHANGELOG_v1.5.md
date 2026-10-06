# Changelog — v1.5 (Data model upgrade)

## Fixed / designed

### 1. Inventory period key renamed
`FactInventorySnapshot` now uses **`PeriodKey`** (YYYYMM) instead of the misleading **`DateKey`** column.
FK target is **`DimPeriod`**, not `DimDate`. Daily facts continue to use `DimDate.DateKey`.

### 2. DimPeriod and DimLocation published
Generator writes `output/DimPeriod.csv` and `output/DimLocation.csv` for clean star-schema joins.

### 3. Impact primary-line grain documented and asserted
`FactImpact_ProductPeriod` remains grain **Product × Period**. `LineID` is the **primary/allocated** line for that product-month (not multi-line explosion). New integrity check: `impact_one_primary_line_per_product_period`.

### 4. SQLite referential integrity
`05_build_sqlite_with_keys.py` rebuilds `oee_revenue_cm_model.db` with:
- Primary keys on dims, bridge, base facts, Impact, PVM
- Foreign keys (PRAGMA foreign_keys=ON)
- Orphan-insert rejection verified

## Pipeline order
```text
01_generate → 02_engine → 03_sensitivity → tests → 05_sqlite → 04_executive_pack
```

Analytical baseline KPIs are unchanged in definition from v1.4; only schema naming and DB constraints are upgraded.
