# OEE → Revenue → Contribution Margin Pipeline

**Version 1.9.0.1** — imaginary dairy factory domain skin · [نسخه فارسی / Persian README](README.fa.md) · `streamlit run dashboard/app_fa.py` — star-schema data model: `PeriodKey` on inventory, `DimPeriod`/`DimLocation`, SQLite PK/FK.

**Synthetic operations-to-finance analytics portfolio project**

This project demonstrates how manufacturing OEE losses can be translated into **unit gaps**, **shipment shortfalls**, **revenue exposure**, and **contribution-margin impact** — with inventory roll-forward, recovery/substitution logic, PVM reconciliation, scenario analysis, and audit-style integrity checks.

> **Data is synthetic.** All figures are model outputs under documented assumptions, not claims about a real plant.

> **Framing:** All financial opportunity figures are **Modeled / assumption-driven / not a forecast**.

> **Authoritative numbers:** treat [`final/Executive_Summary_Numbers.json`](final/Executive_Summary_Numbers.json) as the source of truth after any run (not screenshots, not old LinkedIn drafts). README tables are derived from that file.

> **So what:** Modeled Net CM opportunity ~**$1.28M**. After an **attributed incremental holding proxy** (~$0.02M) → ~**$1.26M**. After **total FG** holding (~$0.86M) → ~**$0.43M** (context only — not proven OEE-caused). **In this synthetic scenario**, inventory policy can materially change the economics of OEE recovery. See `final/EXECUTIVE_CASE_STUDY.md`.

> **History:** [CHANGELOG.md](CHANGELOG.md) · detailed notes in [`docs/changelog/`](docs/changelog/)

---

## Domain (dairy)

| Element | In this model |
|---------|----------------|
| Plant | North Valley Dairy (synthetic) |
| SKUs | Fresh milk 1L/2L, yogurt cups/drinkable, white cheese, butter |
| Lines | Milk fillers, yogurt cup line, cheese/butter pack |
| Stores | Main cold store + dispatch dock |
| Downtime | CIP, changeover, filler fault, quality hold, raw milk shortage |
| UoM | Retail packs (EA); `LitersPerUnit` on DimProduct for volume story |
| Holding | Capital/WACC proxy on cold FG (not full FEFO/expiry engine) |
| COGS | VC = raw milk + packaging + process energy + other (see `docs/COGS_AND_BOM.md`) |


## Business design (one step before the data)

These documents define **what decision the model supports** before synthetic tables are interpreted as answers:

| Doc | Purpose |
|------|---------|
| [`docs/DECISION_BRIEF.md`](docs/DECISION_BRIEF.md) | Owner, actions (buffer / recover / divert / accept), objective, constraints |
| [`docs/PROCESS_AND_CAUSAL_MAP.md`](docs/PROCESS_AND_CAUSAL_MAP.md) | Dairy process path, loss tree, causal chain, confounders |
| [`docs/KPI_TREE.md`](docs/KPI_TREE.md) | From realized CM benefit down to OEE drivers |
| [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) | What each fact group is *for*; future data needs |
| [`docs/COGS_AND_BOM.md`](docs/COGS_AND_BOM.md) | Variable COGS split + shallow BOM; shares vs USDA-style farm/retail structure |

**Decision in one line:** weekly planning chooses interventions to improve **modeled net CM** versus doing nothing—not to optimize a vanity OEE%.

## Business problem

At **North Valley Dairy** (imaginary), many OEE dashboards stop at a percentage. The filling hall sees “OEE = 84%” but commercial and finance cannot answer:

- How many **retail packs / liters** of milk or yogurt did we fail to ship?
- After **cold-store buffer** and **OT / alternate filler**, what is still unmet?
- What **contribution margin** is at risk on those shortfalls?
- Which **SKU–month** is worth overtime or capacity moves after recovery cost?

This pipeline closes that gap for a **synthetic dairy** case — not a real plant extract.

---

## Approach

```text
OEE (A × P × Q)
  → good production capacity
  → production gap (FirmDemand − PrimarySupply)
  → opening-inventory absorption
  → recovery + valid alternate-line substitution
  → residual lost sales
  → revenue exposure & CM exposure
  → net CM opportunity after recovery cost
```

**Design choices (intentional):**

| Choice | Rationale |
|--------|-----------|
| OEE never × revenue | Avoids a common but invalid shortcut |
| CM = NetRevenue − standard variable cost | Managerial contribution, not IFRS gross profit |
| Same-period ship allowed | Simplified ATP; documented limitation |
| Synthetic data | Full control of shortfalls and reproducibility |

---

## Key results (FY2024 synthetic run)

> Regenerated from `final/Executive_Summary_Numbers.json` (script_version **1.9.0**). Do not edit cells by hand.

| KPI | Value |
|-----|------:|
| Time-weighted OEE | **83.98%** |
| Actual net revenue | **$209.97 M** |
| Actual contribution margin | **$61.66 M** |
| Gross production gap | 133,743 EA |
| Opening inventory absorbed | **18,424 EA** |
| Recovered units | **23,064 EA** |
| Substituted units | **45,288 EA** |
| Potential lost sales | **46,967 EA** |
| CM exposure (residual lost sales) | **$1.32 M** |
| Protected CM (recovery + substitution) | **$2.09 M** |
| Recovery cost (stepped) | **$0.80 M** |
| **Net CM opportunity** | **$1.28 M** |
| Incremental holding proxy | **$0.02 M** |
| **Net CM after incremental holding** | **$1.26 M** |
| Total FG holding cost (context) | **$0.86 M** |
| **Net CM after total FG holding** | **$0.43 M** |

### Opportunity bridge (important)

```text
Net CM opportunity  ≠  CM exposure − recovery cost

Net CM opportunity  =  Protected CM − recovery cost
```

- **CM exposure** = margin on units still lost after mitigation  
- **Protected CM** = margin on units saved via recovery/substitution
- **Opening inventory** is applied to the current-period production shortfall; closing inventory is never used to absorb the same period's demand
- **Alternate-line substitution** is allowed only when the capability bridge contains a different physical line from the primary line  
- **Modeled net CM opportunity** = protected CM from modeled recovery/substitution minus recovery cost; it is not total company financial opportunity  

### Insights

1. **High OEE does not mean zero financial leakage.** ~84% OEE coexists with ~47k residual lost-sales units and ~$1.32M residual CM exposure after opening-inventory absorption, recovery, and valid line substitution.
2. **Scenario economics depend on both operational improvement and mitigation cost.** Under stepped recovery costs, the modeled +1pt OEE case can still be net negative after mitigation cost, while larger OEE improvements become positive in this synthetic scenario.
3. **Money concentrates on high-CM, capacity-tight products** (e.g. P1/P3 on bottleneck periods) — prioritization should be financial and capacity-aware, not plant-average OEE.

### Recovery fraction sensitivity (model output)

From `final/Sensitivity_RecoveryFrac.csv` (same engine assumptions):

| Recovery fraction | Recovered units | Protected CM | Recovery cost | Net CM opportunity |
|------------------:|----------------:|-------------:|--------------:|-------------------:|
| 10% (conservative) | 11,532 | $1.75 M | $0.66 M | **$1.09 M** |
| 20% (baseline) | 23,064 | $2.09 M | $0.80 M | **$1.28 M** |
| 40% (optimistic) | 46,128 | $2.51 M | $1.01 M | **$1.50 M** |

Baseline `RECOVERY_FRAC = 0.20` is a **modeling assumption**, not an estimated plant parameter. In dairy terms, recovery means **overtime and alternate filler divert**, not rework of spoiled milk.

**How you would fit `RECOVERY_FRAC` with real data (not implemented here):**
1. Tag downtime/loss events by category (planned changeover vs unplanned breakdown).
2. Join each event to subsequent production and shipment outcomes over a recovery window (e.g. 0–14 days).
3. Estimate the fraction of the gap closed by overtime, resequence, or alternate-line moves — by category, not as one global rate.
4. Optionally use survival / lag models (time from event to first recovered shipment) instead of a single scalar.
5. Re-run sensitivity with confidence intervals; keep the $ bridge explicit (units × CM − mitigation cost).

---

## Repository layout

```text
README.md
DATA_DICTIONARY.md
01_generate_synthetic_data_fixed.py   # synthetic facts + dimensions
02_oee_revenue_cm_engine_fixed.py     # OEE, impact, PVM, scenarios, checks
04_build_executive_pack.py              # presentation-only executive pack + charts
03_sensitivity_recovery.py            # RECOVERY_FRAC sensitivity
07_baseline_vs_action.py              # Baseline vs Action + P_REALIZE + CM/hour
08_downtime_reason_pareto.py          # Downtime reason minutes Pareto
tests/test_fixture_two_period.py      # manual expected-value fixture
config is written to output/:
  ModelAssumptions.csv
  ScenarioParameters.csv
output/   # dimensions & facts (included in this package as a reference snapshot;
          # regenerated fresh by 01_generate_synthetic_data_fixed.py on every run)
final/    # analytics outputs, integrity, SQLite
```

---


## CM vs modeled Gross Profit (v1.9.0)

| Metric | Meaning |
|--------|---------|
| **Contribution margin (CM)** | Net revenue − standard variable cost (managerial) |
| **Modeled gross profit (GP)** | Revenue − modeled COGS including yield variance at std cost |

These are **different views**. Do not treat Actual CM and Actual GP as interchangeable. OEE mitigation economics use **CM**; the P&L bridge uses **modeled GP**.

## How to run (full regenerable pipeline)

**Recommended (one command):**

```bash
python run_pipeline.py
# python run_pipeline.py --skip-tests
# python run_pipeline.py --from 07
# python run_pipeline.py --list
```

**After the pipeline finishes**, open the dashboard (reads `final/` only):

```bash
streamlit run dashboard/app.py
# Persian UI:
streamlit run dashboard/app_fa.py
```

### Manual step order

```bash
python 01_generate_synthetic_data_fixed.py
python 02_oee_revenue_cm_engine_fixed.py
python 03_sensitivity_recovery.py
python 06_sensitivity_same_period_ship.py
python 07_baseline_vs_action.py
python 08_downtime_reason_pareto.py
python 09_finance_decision_artifacts.py   # P_REALIZE sens, budget recon, decision_logic_checks
python 10_pl_bridge.py
python tests/test_fixture_two_period.py
python tests/test_decision_baseline_action.py
python tests/test_pl_bridge.py
python 05_build_sqlite_with_keys.py
python 04_build_executive_pack.py       # after 07–10 so Decision + P&L layer are included
```

Order matters: **04 must run after 07–10**. Prefer `run_pipeline.py` so step order stays correct.


## What the integrity layer checks

Arithmetic and domain controls (all PASS on the reference run), including:

- OEE ∈ [0, 1]
- Inventory mass balance & opening→closing continuity
- Demand-gap waterfall at full precision  
  `GrossGap = InvAbsorbed + Recovered + Substituted + LostSales`
- `NetCMOpportunity = ProtectedCM − RecoveryCost`
- PVM identity at Product×Period and total
- Sales ≤ firm demand
- Price ≥ variable cost (domain)
- No infinite ROI (NaN + status flag when investment = 0)

See `final/integrity_checks.json`.

---

## v1.7 economic extensions

- **Stepped recovery cost** (default `RECOVERY_COST_MODE=STEPPED`): $2 / $7 / $14 per EA by gross-gap band (first 5%, next to 15%, remainder). `FLAT` mode still uses `RECOVERY_COST_UNIT`.
- **Inventory holding cost**: monthly `AvgInventory × StandardVariableCost × (WACC/12)`; `NetCM_after_Holding = NetCMOpportunity − HoldingCost`.
  Holding is charged on **total** average FG, not only OEE-driven extra buffer (documented intentional choice).

## Assumptions

| Parameter | Value / rule | Source |
|-----------|----------------|--------|
| Data | **Synthetic** (not a real plant extract) | design |
| `RECOVERY_FRAC` | 0.20 baseline; sensitivity at 0.10 / 0.20 / 0.40 | `ModelAssumptions.csv` |
| `RECOVERY_COST_MODE` | **STEPPED** (default): tiers $2 / $7 / $14 | `ModelAssumptions.csv` |
| `RECOVERY_COST_UNIT` | $8 / EA when mode = FLAT | `ModelAssumptions.csv` |
| `HOLDING_COST_ANNUAL_WACC` | 18% annual proxy | `ModelAssumptions.csv` |
| `StandardVariableCost` | Fixed synthetic standards; CM ≈ 28–41% of list price by product | `DimProduct` |
| Same-period ship | Allowed (no lead time / backlog) | `SAME_PERIOD_SHIP=1` |
| CM metric | Managerial CM before fixed costs | NetRevenue − Standard VC |

All financial figures are **model results under these assumptions**, not business claims about a real company.

## Dashboard (Streamlit)

```bash
pip install -r dashboard/requirements-dashboard.txt
streamlit run dashboard/app.py
```

Pages: Executive · Product deep dive · Sensitivity · Scenarios.  
Reads `final/` + `output/` only (does not re-run the pipeline).

## Limitations (explicit)

- Synthetic data — illustrative, not calibrated to a real factory  
- No production lead time / backlog carry-over (unmet demand is treated as in-period loss risk)  
- Recovery cost is a **tiered unit cost**, not a full project / CAPEX model  
- **Total FG holding** is context/sensitivity; **incremental holding** is an **attributed proxy** on absorbed units — not a full baseline-vs-mitigation inventory counterfactual  
- CM excludes fixed overhead, depreciation, and allocated SG&A  
- Probability of capture and time-to-realize are not modeled  
- Interactive exploration via Streamlit (`dashboard/app.py`); static charts still in `final/charts/`

Suitable for **portfolio demonstration, methodology design, and dashboard prototyping** — not as a production financial system of record.

## Methodology references

- Metric definitions, PVM method, inventory identities: `DATA_DICTIONARY.md`
- Resolved assumptions for a run: `output/ModelAssumptions.csv` + `final/integrity_checks.json` → `resolved_config`
- Executive numbers + bridges: `final/Executive_Summary_Numbers.json`

## Scenario narratives (directional)

| Label | Example IDs | Why it differs |
|-------|-------------|----------------|
| **Base** | Engine baseline Impact | Current synthetic operating point (RECOVERY_FRAC=20%, same-period ship on) |
| **Optimistic** | e.g. S5 OEE +5pt; higher recovery multiplier | Assumes reliability and/or recovery capacity improve — more gap closed before lost sales |
| **Stressed** | e.g. SDP demand +10% | Demand outruns primary + mitigation capacity — exposure rises even if OEE is unchanged |

These are **illustrative parameter shifts**, not approved business cases.

## What's next (not in scope yet)

| Idea | Why |
|------|-----|
| Fit `RECOVERY_FRAC` from real event→shipment lags | Replace assumed 20% with estimated recovery by loss category |
| Multi-period backlog / partial late fulfillment | Soften “all shortfall = lost sales” |
| Multi-plant / multi-warehouse extension | Same grain model, more dimensions |
| Demand forecast error vs firm demand | Separate planning bias from OEE loss |
| Optional ML downtime risk layer | Predict unplanned loss; still keep $ bridge explicit |

These are extensions, not admissions that the current chain is wrong.

## Dependencies

```bash
pip install -r requirements.txt                  # pipeline
pip install -r dashboard/requirements-dashboard.txt  # Streamlit UI
# or: pip install -r requirements-dev.txt
```
