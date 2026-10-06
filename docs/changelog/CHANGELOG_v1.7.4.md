# Changelog — v1.7.4

## Fix (N1): engine vs sensitivity recovery cost

- Extracted `mitigation_cost` to **`shared/cost_model.py`** (single source of truth).
- Sensitivity now sizes stepped tiers against **GrossGap** (same as engine).
- Baseline row (frac=0.20) matches engine exactly: RecoveryCost **654,490.40**, NetCM **1,118,372.29**.
- Sensitivity column renamed to `FlatModeUnitCost` (only used in FLAT mode).

## Docs

- DATA_DICTIONARY: tier reference = GrossGap; product-grain holding semantics clarified.
- README sensitivity table reconciled with engine KPIs.
