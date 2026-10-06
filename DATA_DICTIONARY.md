# Data Dictionary — OEE → Revenue → CM Synthetic Pipeline

**Version:** 1.1-fixed  
**Data type:** SYNTHETIC (not a real plant extract)
**Currency:** USD (synthetic)  
**Volume unit:** EA (each)  
**Time grain (facts):** calendar month = `PeriodKey` = `YYYYMM`  
**Run scope:** FY2024 (2024-01 through 2024-12)

---

## 1. Metric definitions

### OEE (Overall Equipment Effectiveness)
```
Availability = RunTime_h / PlannedProductionTime_h
Performance  = StandardCycleTime_h * TotalUnits / RunTime_h
Quality      = GoodUnits / TotalUnits
OEE          = Availability × Performance × Quality   ∈ [0, 1]
```
- Changeover time is inside **Availability** (reduces RunTime).
- Rework is inside **Quality** (does not increase GoodUnits).
- **OEE is never multiplied by revenue.** Capacity effects are converted to units, then to money only via demand, shipments, and price/CM.

### Contribution Margin (CM)
```
CM = NetRevenue − VariableCost
```
**Included (standard, product-level):**
- Variable cost = `DimProduct.StandardVariableCost` × units

**How StandardVariableCost was set (synthetic design rule):**
| Product | Price | Variable cost | CM | CM % of price |
|---------|------:|--------------:|---:|--------------:|
| P1 Widget A | 100 | 62 | 38 | 38% |
| P2 Widget B | 85 | 50 | 35 | 41% |
| P3 Widget C | 120 | 80 | 40 | 33% |
| P4 Gear X | 60 | 38 | 22 | 37% |
| P5 Gear Y | 75 | 49 | 26 | 35% |
| P6 Gear Z | 95 | 66 | 29 | 31% |
| P7 Housing M | 150 | 105 | 45 | 30% |
| P8 Housing L | 180 | 130 | 50 | 28% |

Design intent: **CM margin roughly 28–41% of list price**, higher on simpler Alpha widgets,
lower on Gamma housings (more conversion content). Values are **not** from a real ERP;
they are fixed synthetic standards so scenario comparisons isolate volume/OEE effects
rather than cost revaluation.

Implied cost stack represented by the single standard VC number:
- direct material (majority)
- variable conversion (labor/energy proxy)
- **not** packaging freight commissions as separate lines

**Explicitly NOT included in CM:**
- Fixed manufacturing overhead
- Allocated SG&A
- Capital / depreciation
- Recovery implementation cost (tracked separately as `RecoveryCost`)

Costs are **standard**, not actual; applied at **sales time** (shipment units), not production time.
Preferred reporting name: **Managerial Contribution Margin Before Fixed Costs**.

### Net Revenue
```
NetRevenue = GrossRevenue − Discount − Returns − Allowances
```
Synthetic commercial adjustments only; no tax or FX.

### PVM (Price–Volume–Mix) bridge methodology
Grain: **ProductID × PeriodKey**

Reference price for volume/mix:
```
pB = Σ BudgetRevenue / Σ BudgetVolume   (portfolio budget average price)
BPrice_i = BudgetRevenue_i / BudgetVolume_i
```

Effects:
```
VolumeEffect_i = (ActualUnits_i − BudgetUnits_i) × pB
MixEffect_i    = ActualUnits_i × (BPrice_i − pB)
PriceEffect_i  = ActualUnits_i × (ActualAvgPrice_i − BPrice_i)
Residual_i     = ActualRevenue_i − (BudgetRevenue_i + Volume + Mix + Price)_i
```

Identity (asserted per group and total):
```
ActualRevenue − BudgetRevenue
  = VolumeEffect + MixEffect + PriceEffect + Residual
```

- New / discontinued products: outer join; missing side filled with 0.
- Zero-volume products: BPrice/APrice treated as 0; effects collapse to 0.
- Mix uses **budget** portfolio price `pB` as the mix reference (standard “budget-mix” style).

Tolerance for assertion:
- Absolute: 0.05 USD  
- Relative: 1e-9 × |ExpectedDelta|

---

## 2. Inventory & flow definitions

**Column naming (v1.5):** `FactInventorySnapshot` uses **`PeriodKey`** (YYYYMM), not `DateKey`.
Daily keys remain only on production/downtime/sales facts via `DimDate.DateKey`.



Grain: **ProductID × PeriodKey** (location split is presentational only)

```
ClosingInventory = OpeningInventory + GoodProduction − Shipments
OpeningInventory[t+1] = ClosingInventory[t]
```

| Term | Meaning in this model |
|------|------------------------|
| **GoodProduction** | Good units from FactProduction (after scrap), summed to month |
| **Shipments** | Units shipped to customers = FactSales quantity |
| **Sales** | Same as Shipments (invoiced ≈ shipped; no lag modeled) |
| **FirmDemand** | Committed demand target for the month |
| **Opening / Closing** | Finished-goods inventory at period boundaries |
| **FGInventory** | Closing FG split across warehouses |
| **BlockedInventory** | Portion of FG not usable |
| **UsableInventory** | FG − Blocked (from final rounded integers) |
| **OpeningAvailableInventory** | Opening inventory treated as available to fulfill current-period FirmDemand in this synthetic same-period-shipping model |
| **AbsorbableInventory** | max(0, Usable − SafetyStock) on the closing inventory snapshot; retained as a descriptive closing-balance field and **not** used to absorb the same period's demand gap |
| **Returns / transfers / adjustments** | **Not modeled** |

Same-period production **can** ship in the same period (no lead-time model).

---

## 3. Opportunity chain (operational → financial)

```
Loss (downtime / speed / quality)
  → Lost capacity (hours × rate)
  → GrossGap units (FirmDemand − PrimarySupply)
  → after OpeningAvailableInventory absorption
  → after RecoveredUnits + SubstitutedUnits
  → PotentialLostSalesUnits
  → RevenueExposure = LostUnits × ExpNetPrice
  → CMExposure      = LostUnits × CMUnit
```

Layered opportunity fields (see Opportunity_Prioritization):
- `TheoreticalCapacityGapUnits` ≈ GrossGap before inventory
- `DemandConstrainedGapUnits` = GrossGap − InventoryAbsorbed, where InventoryAbsorbed is sourced from OpeningAvailableInventory
- `ShipmentGapUnits` ≈ PotentialLostSalesUnits
- `RevenueOpportunity` = RevenueExposure
- `CMOpportunity` = CMExposure  (**CM of residual lost sales only**)
- `ProtectedCM` = CM of RecoveredUnits + SubstitutedUnits (mitigated gap)
- `RecoveryCost` = (Recovered + Substituted) × RECOVERY_COST_UNIT
- `NetCMOpportunity` = **ProtectedCM − RecoveryCost**

**Important identity (asserted):**
```
NetCMOpportunity ≠ CMExposure − RecoveryCost
NetCMOpportunity = ProtectedCM − RecoveryCost
```
`CMExposure` is the remaining risk after mitigation.
`NetCMOpportunity` is the net value of the mitigation actions themselves.

**Demand-gap waterfall (asserted at full precision):**
```
GrossGap = InventoryAbsorbed + RecoveredUnits + SubstitutedUnits + PotentialLostSalesUnits
```

---

## 4. Fact / dimension grains

| Table | Grain | Business key |
|-------|-------|--------------|
| DimDate | Day | DateKey |
| DimProduct | Product | ProductID |
| DimLine | Line | LineID |
| DimEquipment | Equipment | EquipmentID |
| DimDowntimeReason | Reason | DowntimeReasonID |
| DimScenario | Scenario | ScenarioID |
| Bridge_ProductLineCapability | Product × Line | ProductID + LineID |
| FactProduction | Run | ProductionRunID |
| FactDowntime | Event | DowntimeEventID |
| FactDemand | Period × Product × DemandType × Scenario | composite |
| FactSales | Transaction | SalesTransactionID |
| FactInventorySnapshot | Period × Product × Location | composite |
| FactFinancialPlan | Period × Product × Scenario | composite |
| FactOEE_Run | Run | ProductionRunID |
| FactImpact_ProductPeriod | Period × Product | PeriodKey + ProductID |
| PVM_Bridge | Period × Product | PeriodKey + ProductID |

---

## 5. Scenario parameters

Stored in `output/ScenarioParameters.csv` (not hard-coded only).  
Engine reads this file; coefficients are versioned with the run.

| ScenarioID | Meaning |
|------------|---------|
| S0 | Baseline |
| S1 / S3 / S5 | OEE +1 / +3 / +5 percentage points (output uplift ≈ pts / OEE) |
| SD10 | Unplanned downtime −10% ≈ +2% output |
| SQ | Recover 30% of scrap as good units |
| SDP | Firm demand +10% |
| SR | Recovery fraction × 1.5 |
| S3S5 | **Not used** — original ID was a typo with no business definition |

---

## 6. Semantic nulls

| Value | Meaning |
|-------|---------|
| 0 | Real measured/calculated zero |
| NaN / NULL | Not calculable or not applicable |
| Infinity | **Not emitted** in financial outputs |
| RecoveryROI = NaN + Status flag | Zero investment / undefined ROI |

---

## 7. Limitations (explicit)

- Synthetic data; distributions are illustrative, not plant-calibrated.
- No multi-echelon lead time, no backlog carry of lost sales into future periods.
- Recovery cost is a flat $/unit assumption, not a project cost model.
- Probability of capture and time-to-realize are not estimated (priority score is CM-based only).
- Suitable for prototyping, training dashboards, and methodology testing — not a production financial system of record.


### Critical modeling rules (v1.2, extended v1.4)

1. **Opening inventory, not closing inventory, absorbs current-period demand shortfalls.** Closing inventory is the residual after shipments and therefore cannot be reused as same-period supply.
2. **Alternate-line substitution requires a distinct physical line.** If a product has only one capable line, `AltLineID` is null and no substitution is credited.
3. **Recovery is independent of alternate-line capability.** Generic recovery and line substitution are separate mitigation mechanisms.
4. **Sales reconciles exactly to shipments.** Synthetic transaction allocation uses integer multinomial allocation so `SUM(FactSales.Units) = Shipments` at ProductID × PeriodKey.
5. **Alternate-line slack is a finite, shared resource (v1.4).** Available slack hours on an `AltLineID` are tracked per `(PeriodKey, AltLineID)` and decremented as products claim substitution, so two products sharing the same alternate line in the same period cannot both be credited against the same hours. Within a period, scarce slack is allocated CM-per-unit descending. Enforced by the `alt_line_slack_not_oversubscribed` integrity check.


## Impact grain and LineID (v1.5)

`FactImpact_ProductPeriod` grain is **ProductID × PeriodKey** (one row per product-month).

`LineID` on that table is the **primary / allocated line** for the product in that month
(from capability bridge / production concentration), **not** a full multi-line operational grain.
If a product ran on multiple lines in the same month, those lines are not exploded into separate
Impact rows in this model.



## Inventory holding cost (v1.7)

Monthly holding cost per product-period:

```text
AvgInventory = (OpeningInventory + ClosingInventory) / 2
HoldingCost  = AvgInventory × StandardVariableCost × (HOLDING_COST_ANNUAL_WACC / 12)
```

`NetCM_after_Holding = NetCMOpportunity − HoldingCost` (still managerial; not full EVA/IFRS).

## Stepped recovery cost (v1.7)

When `RECOVERY_COST_MODE=STEPPED`, mitigated units (recovered + substituted) are costed in bands of the gross gap:

| Band | Default | Cost |
|------|---------|-----:|
| Tier 1 | first 5% of gap | $2/EA |
| Tier 2 | next up to 15% of gap | $7/EA |
| Tier 3 | remainder | $14/EA |

`FLAT` mode uses single `RECOVERY_COST_UNIT`.


## Stepped recovery cost — tier reference (v1.7.4)

Tier bands are sized against **GrossGap** (pre–inventory absorption), not residual gap after absorption.
This is the single canonical rule used by both the engine (`02`) and sensitivity (`03`) via `shared/cost_model.py`.

With defaults (`RECOVERY_FRAC=0.20`, `TIER2_FRAC=0.15`), baseline recovery already exhausts the cheap tiers:
marginal recovered units beyond ~15% of GrossGap are priced at **tier-3 ($14/EA)**.

`FlatModeUnitCost` in sensitivity output applies only when `RECOVERY_COST_MODE=FLAT`.

## NetCM_after_Holding at product grain (semantics)

`HoldingCost` on `FactImpact_ProductPeriod` is each product-period's share of carrying cost on **that product's** average FG inventory (Opening+Closing)/2 × VC × (WACC/12) — not a reallocation of portfolio total by gap.

It is an **attributed cost proxy**, **not** a full baseline-versus-mitigation inventory counterfactual, and **not** "holding cost caused by OEE loss alone." Portfolio ranking by `NetCM_after_Holding` mixes mitigation value with ordinary inventory carrying. Prefer portfolio totals in the executive summary for the inventory-policy story; use product-level `NetCMOpportunity` for prioritization of recovery actions.


## PVM semantic specification

Bridge compares **Actual** (realized synthetic sales) vs **Budget** (plan from FactFinancialPlan) at Product×Period.

| Effect | Meaning (this model) |
|--------|----------------------|
| Volume | Change in units × budget price (reference price) |
| Mix | Residual volume structure vs budget mix at budget prices |
| Price | (Actual price − budget price) × actual units |
| Residual | Arithmetic residual after Vol+Mix+Price (should be ~0) |

Sign: positive effect increases actual revenue vs budget. Residual is numerical, not a separate economic interaction term.

## Figure classification

| Label | Meaning |
|-------|---------|
| Observed | Not used — all operational facts are **synthetic generated** |
| Calculated | Deterministic transform of synthetic inputs (e.g. OEE = A×P×Q) |
| Assumption | Parameter from ModelAssumptions (e.g. RECOVERY_FRAC) |
| Modeled opportunity | Scenario-dependent mitigation value — **not a forecast** |


## Fitting RECOVERY_FRAC (methodology note — not implemented)

With plant data: classify loss events → join to production/shipment recovery windows → estimate gap-closure rates by category (planned vs unplanned) → optional lag/survival models → feed rates into the same unit×CM−cost bridge. The portfolio uses a single assumed scalar for transparency only.


## COGS components (v1.8.2)

On `DimProduct`:

| Column | Description |
|--------|-------------|
| RawMilkCost | Variable raw milk $ / EA |
| PackagingCost | Primary pack $ / EA |
| ProcessingEnergyCost | Process/CIP energy proxy $ / EA |
| OtherVariableCost | Culture/aux/misc variable $ / EA |
| StandardVariableCost | Sum of the four (identity) |

`Bridge_BOM.csv`: shallow product→component qty; costing uses DimProduct money fields.

See `docs/COGS_AND_BOM.md` for calibration notes (USDA ERS farm-share context).
