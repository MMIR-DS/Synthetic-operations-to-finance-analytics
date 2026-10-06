# Executive Case Study — OEE → Revenue → Contribution Margin

**Portfolio version: 1.9.0** · Modeled / synthetic · not a forecast

## So what (read this first)

| Story layer | Number | Meaning |
|-------------|-------:|---------|
| Residual CM **exposure** | **$1.32M** | Margin on units still expected lost after mitigation path |
| Modeled **net CM opportunity** | **$1.28M** | Protected CM − stepped recovery cost |
| Inventory **holding cost** | **$0.86M** | Avg FG × VC × (WACC/12); total FG not only OEE buffer |
| **Net CM after holding** | **$0.43M** | Opportunity left after capital/storage proxy |

**Primary insight:** the modeled economics are highly sensitive to how inventory carrying cost is treated
($1.28M → $0.43M). In this synthetic case, **inventory policy can matter as much as OEE recovery**—especially under a total-FG holding proxy.

**Budget context:** actual CM **$61.66M** vs budget **$85.15M** → about **$23.5M** CM shortfall vs plan. Residual CM exposure is a **partial** explanation of that miss (see also PVM).

**Critical assumption:** `RECOVERY_FRAC = 0.2` is a modeling input, not a fitted plant probability.
With real data: estimate by loss category from downtime→shipment lags (or survival on recovery windows); do not use one global rate forever.

**Figure class:** all $ figures below are **Modeled / assumption-driven / scenario-dependent — not a forecast and not realized benefit.**

**Holding cost — three interpretations:**
| View | Approx. | Use |
|------|--------:|-----|
| No holding | **$1.28M** | Mitigation value only |
| After incremental holding (**attributed proxy**) | **$1.26M** (incr. cost ~$0.02M) | Not a full inventory counterfactual |
| After total FG holding | **$0.43M** | Full carrying cost (can over-penalize recovery) |

## Budget CM shortfall vs OEE-path exposure

| Item | Modeled |
|------|--------:|
| Budget CM shortfall (plan − actual) | **$23.49M** |
| Residual CM exposure (after mitigation waterfall) | **$1.32M** |
| Residual CM exposure as share of budget-to-actual CM gap *(not causal attribution)* | **5.6%** |
| Remainder (other drivers — not claimed as OEE opportunity) | **$22.17M** |

Do **not** equate the budget miss with OEE opportunity. Detail: `final/Budget_CM_Gap_Reconciliation.md`.

### CM vs modeled Gross Profit (v1.9 — do not interchange)

| View | Definition | Current |
|------|------------|--------:|
| **Contribution margin** | Net revenue − standard variable cost (managerial) | Actual CM **$61.66M** |
| **Modeled GP** | Revenue − modeled COGS (std VC + yield variance) | Actual GP **$46.55M** |

OEE mitigation economics use **CM**. The P&L bridge uses **modeled GP**. Different cost bases.

### Modeled standard-cost P&L bridge (v1.9)

| Item | Amount |
|------|-------:|
| Budget → Actual revenue | **$247.70M** → **$209.97M** |
| Volume / Price effects | **$-21.77M** / **$-15.96M** |
| Yield variance | **$7.94M** |
| Budget GP → Actual GP | **$85.15M** → **$46.55M** (var **$-38.60M**) |

Product-level MixEffect = 0 (SKU grain). No fixed overhead / EBITDA.

### P_REALIZE sensitivity (on net operational CM $1.28M)

| P | Expected risk-adjusted |
|--:|-----------------------:|
| 0.40 | **$0.51M** |
| **0.65 (baseline)** | **$0.83M** |
| 0.85 | **$1.09M** |
| 1.00 | **$1.28M** |

`P_REALIZE` is an **assumption-based realization factor**, not a fitted probability. Table: `final/Sensitivity_P_Realize.csv`.

## Baseline vs Action (decision economics)

| View | Modeled $ | Meaning |
|------|----------:|---------|
| Baseline CM exposure (inventory only) | **$3.41M** | If no OT recovery / divert |
| Action CM exposure | **$1.32M** | After recovery + substitution |
| Exposure avoided by action | **$2.09M** | Baseline − action exposure |
| Net operational CM (action) | **$1.28M** | Protected CM − recovery cost |
| Risk-adjusted (× P_REALIZE=0.65) | **$0.83M** | Assumption, not fitted |

SKU–period detail: `final/Decision_Action_Comparison.csv`. Positive Δ net on **37** of **96** product-periods.

**2-minute verbal arc:** problem (OEE% ≠ $) → key number (**$0.43M after total holding**) → assumption (recovery frac) → with real data, fit recovery empirically; do not present as guaranteed P&L benefit.


---

## Decision question
**When does an operational loss actually become a financial loss?**

This synthetic case study is set in an **imaginary dairy factory** (fillers, cold stores, CIP). It connects manufacturing performance to financial exposure without multiplying OEE by revenue. Recovery = overtime / alternate filler — not rework of spoiled milk.

## Baseline snapshot

| KPI | Result |
|---|---:|
| Time-weighted OEE | **83.98%** |
| Actual net revenue | **$209.97M** |
| Actual contribution margin | **$61.66M** |
| Gross production gap | **133,743 EA** |
| Opening inventory absorbed | **18,424 EA** |
| Recovered units | **23,063 EA** |
| Substituted units | **45,287 EA** |
| Potential lost sales | **46,967 EA** |
| Residual CM exposure | **$1.32M** |
| Protected CM | **$2.09M** |
| Recovery cost | **$0.80M** |
| Modeled net CM opportunity | **$1.28M** |
| Inventory holding cost | **$0.86M** |
| **Net CM after holding** | **$0.43M** |

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
