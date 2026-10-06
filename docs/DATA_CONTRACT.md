# Data Contract — North Valley Dairy (synthetic)

**Version:** 1.9.0.1  
**Purpose:** State what data is *for* (decision support), not only table shapes  

Full column-level specs remain in `DATA_DICTIONARY.md` and `DATA_MODEL.md`.

---

## 1. Entities and grains

| Entity | Grain | Business key | Decision use |
|--------|-------|--------------|--------------|
| Product (SKU) | one row per SKU | ProductID | Margin, shelf life, capability |
| Line | one row per line | LineID | Capacity home |
| Period | month | PeriodKey | Planning bucket |
| Date | day | DateKey | Run/downtime/sales events |
| Location | cold store / dock | LocationID | FG state (not flow sum by WH) |
| Scenario | planning scenario | ScenarioID | What-if |

---

## 2. Fact groups → decision questions

| Fact group | Answers |
|------------|---------|
| Production + OEE + Downtime | What stopped or slowed the filler? How many good packs? |
| Demand + Financial plan | What was firm demand / budget? |
| Inventory snapshot | What cold FG was available to absorb a gap? |
| Sales | What shipped (reconciling to inventory logic)? |
| Impact (derived) | Where is the gap, mitigation, CM exposure, opportunity? |
| PVM | Price/volume/mix vs plan (context) |
| Scenarios / sensitivity | How assumptions move the answer? |

---

## 3. Minimum fields for the Decision Brief

| Need | Source |
|------|--------|
| Firm demand | FactDemand / Impact.FirmDemand |
| Primary supply | Impact.PrimarySupply |
| Opening available inventory | Impact.OpeningAvailableInventory |
| Gap waterfall | GrossGap, InventoryAbsorbed, Recovered, Substituted, Lost |
| CM/unit | Impact.CMUnit |
| Opportunity $ | NetCMOpportunity, ProtectedCM, RecoveryCost |
| Capability | Bridge_ProductLineCapability |
| Assumptions | ModelAssumptions.csv |

---

## 4. Quality rules (enforced or documented)

| Rule | Enforcement |
|------|-------------|
| OEE in [0,1] | Integrity checks |
| Gap identity | GrossGap = absorb + recovered + subst + lost |
| NetCM identity | ProtectedCM − RecoveryCost |
| Alt-line slack not oversubscribed | Engine check |
| Sales ≤ firm demand | Check |
| PK/FK in SQLite | 05_build_sqlite_with_keys |
| No OEE×Revenue path | Design + docs |

---

## 5. Future data (not in synthetic set yet)

| Domain | Example fields | Why |
|--------|----------------|-----|
| Quality release | hold_start, release_ts | Same-period ship realism |
| Backlog | open_order_qty, cancel_qty | Soften lost-sales assumption |
| Recovery by reason | recoverable_flag by downtime type | Fit RECOVERY_FRAC |
| Labor | OT hours, crew limits | True OT cost |
| Customer | OTIF, priority tier | Service objective |
| Lots | production_date, expiry | FEFO / shrink |

---

## 6. Lineage (run)

```text
01_generate → output/*.csv
02_engine   → final/Impact, PVM, scenarios, integrity
03 / 06     → sensitivity CSVs
05_sqlite   → oee_revenue_cm_model.db (PK/FK)
04_pack     → EXECUTIVE_CASE_STUDY.md
dashboard   → reads final/ + output/ only
```

---

## 7. Contract statement

> Synthetic data exist to **exercise the decision brief** (buffer / recover / divert / accept shortfall) under explicit assumptions—not to represent a real dairy’s books.
