# Upload status (updated)

Portfolio **v1.9.0.1**

## On GitHub

### Pipeline scripts
- `run_pipeline.py`
- `03_sensitivity_recovery.py`
- `06_sensitivity_same_period_ship.py`
- `07_baseline_vs_action.py`
- `08_downtime_reason_pareto.py`
- `09_finance_decision_artifacts.py`
- `10_pl_bridge.py`
- `shared/cost_model.py`

### Docs & framing
- `README.md`, `CHANGELOG.md`
- `docs/DATA_CONTRACT.md`, `KPI_TREE.md`, `COGS_AND_BOM.md`
- `docs/changelog/CHANGELOG_v1.9.0.1.md`

### Outputs
- `final/Executive_Summary_Numbers.json`
- `final/Decision_Action_Summary.json`
- `final/Budget_CM_Gap_Reconciliation.md`
- `final/decision_logic_checks.json`
- `execution_report.txt`

### Tests
- `tests/test_*.py` (smoke identities)

## Still to upload

| File | Why important |
|------|----------------|
| `01_generate_synthetic_data_fixed.py` | Data generator |
| `02_oee_revenue_cm_engine_fixed.py` | **Core engine** |
| `04_build_executive_pack.py` | Exec pack |
| `05_build_sqlite_with_keys.py` | SQLite PK/FK |
| `dashboard/app.py`, `app_fa.py` | Streamlit UI |
| `DATA_DICTIONARY.md`, full `DECISION_BRIEF`, full `DATA_MODEL` | Docs depth |
| `final/*.csv` | Regenerable via pipeline |

**Note:** Clone alone cannot yet run end-to-end without `01`/`02`. Continue push or upload ZIP from PC.
