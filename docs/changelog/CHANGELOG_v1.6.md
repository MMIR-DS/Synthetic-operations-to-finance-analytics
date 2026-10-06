# Changelog — v1.6

## P1
1. **Single SQLite write path** — engine no longer dumps unkeyed tables; only `05_build_sqlite_with_keys.py` builds the DB with PK/FK.
2. **Mermaid ERD** in `DATA_MODEL.md` as source-of-truth diagram.

## P2
3. **SAME_PERIOD_SHIP** honored in generator roll-forward (0 = opening-only ship).
4. **Sensitivity** `06_sensitivity_same_period_ship.py` → `Sensitivity_SamePeriodShip.csv`.
5. **PRIMARY_LINE_RULE** in `ModelAssumptions.csv` (`PRIMARY_ALLOCATED`).

## Notes
Baseline portfolio run remains `SAME_PERIOD_SHIP=1`. Sensitivity shows the counterfactual without re-baselining executive KPIs.
