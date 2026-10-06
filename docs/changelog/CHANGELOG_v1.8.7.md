# Changelog — v1.8.7

## Reproducibility fix (review finding)

Three `final/` artifacts were only present as static leftovers and were **not** written by any shipped script:

- `Sensitivity_P_Realize.csv`
- `Budget_CM_Gap_Reconciliation.md` / `.json`
- `decision_logic_checks.json`

**Fix:** add `09_finance_decision_artifacts.py` (depends on 02 + 07).

**README How to run** updated: include 07, 08, 09, both test files; **04 after 07–09**.

No change to core opportunity economics.
