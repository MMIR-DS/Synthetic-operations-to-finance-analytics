# Changelog — v1.6.1 (review fixes)

## HIGH
- **H1** `SAME_PERIOD_SHIP` now drives Impact/scenario shippable production (0 → production not credited against same-period demand). Generator reads flag from `ModelAssumptions.csv` (no shadow literal).

## MEDIUM
- **M1** Scenario results column renamed to `NetCMImpact_after_RecoveryCost` (was overloaded `NetCMOpportunity`).
- **M2** Scenario alt-line slack scales `LineReqH` by `Demand_Factor`.
- **M3** SQLite `FactImpact_ProductPeriod` DDL aligned with CSV (ResidualGap, AltLineID, AltRate, CMUnit, ExpNetPrice).

## LOW
- **L3** Removed dead sales groupby in generator.
- **L5** Same-period-ship sensitivity seeds opening from `FactInventorySnapshot`.
