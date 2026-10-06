# Upload status

Portfolio **v1.9.0.1** — partial publish via Grok GitHub connector.

## On GitHub now

- README, CHANGELOG, requirements, `.gitignore`
- `run_pipeline.py`, `shared/cost_model.py`
- `06_sensitivity_same_period_ship.py`, `08_downtime_reason_pareto.py`, `10_pl_bridge.py`
- `tests/` (identity smoke tests)
- `docs/` (DATA_CONTRACT, KPI_TREE, COGS_AND_BOM, changelog 1.9.0.1)
- `final/Executive_Summary_Numbers.json`, `execution_report.txt`, decision_logic_checks

## Still to upload (local package / next push)

- `01_generate_synthetic_data_fixed.py` (~30 KB)
- `02_oee_revenue_cm_engine_fixed.py` (~40 KB) — core engine
- `03_sensitivity_recovery.py`, `04_build_executive_pack.py`, `05_build_sqlite_with_keys.py`
- `07_baseline_vs_action.py`, `09_finance_decision_artifacts.py`
- `dashboard/app.py`, `dashboard/app_fa.py`
- Full `DATA_DICTIONARY.md`, `docs/DECISION_BRIEF.md`, `docs/PROCESS_AND_CAUSAL_MAP.md`
- Remaining `final/*.csv` outputs (regenerate with `python run_pipeline.py`)

## Authoritative numbers (reference run)

- Net CM opportunity: **$1,282,935.17**
- OEE (time-weighted): **83.98%**
- Integrity: **24/24 PASS**

See `final/Executive_Summary_Numbers.json`.
