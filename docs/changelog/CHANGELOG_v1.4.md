# Changelog — v1.4

## Fixed

### 1. Alternate-line slack could be double-claimed across products in the same period
`AltLineID` slack (`LineAvailH − LineReqH`) was previously looked up independently for
every product×period row from a static table, so two products sharing the same alternate
line in the same period could each be credited substitution against the *same* un-consumed
hours. The engine now tracks remaining slack per `(PeriodKey, AltLineID)` and decrements it
as each product claims substitution units, in both the baseline engine and the scenario
loop. Allocation order within a period is CM-per-unit descending, so scarce alternate-line
capacity goes to the highest-value opportunity first.

**Effect on the FY2024 reference run: none.** With the current 8-product/4-line bridge, no
two products ever target the same alternate line in the same period, so no collision existed
in the shipped baseline numbers — this was a latent correctness risk, not a live error. A new
integrity check, `alt_line_slack_not_oversubscribed`, now asserts this holds for any future
data (more products, more shared alternate lines) and would fail loudly if it didn't.

### 2. Stale `sales_demand_rounding_units` tolerance removed from integrity output
`integrity_checks.json → tolerances` still reported a `sales_demand_rounding_units: 2`
constant left over from before the ±2-unit tolerance was removed in v1.3. The check itself
(`sales_le_firm_demand`) was already zero-tolerance; only the reported (unused) constant was
stale. Removed.

### 3. `execution_report.txt` is now generated, not hand-maintained
Previously a static file that could silently drift out of sync with the actual `final/`
outputs (it did — a prior copy reported sensitivity numbers from an earlier run that no
longer matched `Sensitivity_RecoveryFrac.csv`). `04_build_executive_pack.py` now rebuilds
`execution_report.txt` from `final/integrity_checks.json`, `final/Executive_Summary_Numbers.json`,
and `final/Sensitivity_RecoveryFrac.csv` on every run, so it can't go stale again.

## Verification

Full pipeline (`01 → 02 → 03 → tests → 04`) re-run from a clean state reproduces the FY2024
baseline exactly: gross gap 134,788 EA, CM exposure $1,615,013.79, net CM opportunity
$1,310,807.35, 22/22 integrity checks passed (21 from v1.3 + the new oversubscription guard),
11/11 fixture tests passed.

All figures remain synthetic model outputs under the documented assumptions.
