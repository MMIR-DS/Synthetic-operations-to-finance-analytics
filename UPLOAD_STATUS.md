# Upload status

Portfolio **v1.9.0.1**

## On GitHub (usable for story + most decision scripts)

- Orchestration: `run_pipeline.py`
- Scripts: `03`, `06`, `07`, `08`, `09`, `10` + `shared/cost_model.py`
- Docs: README, README.fa, DATA_MODEL, DECISION_BRIEF, PROCESS map, DATA_CONTRACT, KPI_TREE, COGS_AND_BOM
- Outputs: Executive_Summary_Numbers, Decision_Action_Summary, Budget_CM_Gap_Reconciliation, decision_logic_checks, execution_report
- Tests: smoke identity tests

## Still missing for full local run

| File | Size |
|------|------|
| `01_generate_synthetic_data_fixed.py` | ~30 KB |
| `02_oee_revenue_cm_engine_fixed.py` | ~40 KB |
| `04_build_executive_pack.py` | ~17 KB |
| `05_build_sqlite_with_keys.py` | ~17 KB |
| `dashboard/app.py`, `app_fa.py` | ~16–23 KB |
| Full DATA_DICTIONARY | ~14 KB |
| final CSVs | regenerable |

**Next:** push `01`/`02`/`04`/`05`/dashboard, or upload ZIP from PC once.
