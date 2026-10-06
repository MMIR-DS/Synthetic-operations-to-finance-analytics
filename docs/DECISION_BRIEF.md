# Decision Brief — North Valley Dairy (synthetic)

Portfolio **1.9.0.1** · Decision-model baseline **1.9.0**

## Decision

For each SKU–Period, which capacity intervention should planning choose so expected realized CM improves vs doing nothing — without breaking cold-chain/service constraints?

**Not:** plant-wide OEE only, or company P&L forecast.

## Owner

Production / Planning Manager (weekly); logistics, quality, commercial consulted; plant + FP&A informed.

## Grain

- Model: calendar **month × SKU**
- Cadence: weekly review with monthly modeled economics
- PK: `PeriodKey × ProductID` (primary line as attribute)

## Actions

| ID | Action |
|----|--------|
| A0 | Do nothing (baseline) |
| A1 | Use cold-store buffer |
| A2 | Recover on primary (OT / extra run) |
| A3 | Divert to alternate capable line |
| A4 | Accept shortfall |

Engine waterfall = quantitative skeleton of A1–A4.

## Objective

Maximize Net Operational Opportunity ≈ Protected CM − Recovery cost − incremental holding proxy.

Headline: **NetCMOpportunity** (Modeled / not a forecast).

Risk-adjusted = max(0, Net) × **P_REALIZE** (assumption, default 0.65).

## Constraints (in model)

Line rate, capability bridge, SAME_PERIOD_SHIP, RECOVERY_FRAC, stepped recovery cost, holding views.

## Out of scope

Pricing design, major capex, FEFO lot optimization, multi-plant network, guaranteed P&L.
