# Changelog — v1.9.0

## P&L Bridge + BOM / COGS variance (schema-correct)

### Review of external v1.9.0 proposal
Rejected as-is: wrong column names (`ListPrice`, `StandardVC`, `Quantity`, `PlannedVolume`), assumed Dash app, MixEffect forced to 0 without product identity, Budget+Yield=Actual COGS identity invalid.

### Implemented (aligned to live pipeline)
- `DimBOMComponent` + `FactBOMUsage` from existing DimProduct cost fields
- `FactCOGSVariance`: BudgetCOGS + VolumeCOGSEffect + YieldVariance = ActualCOGS
- `10_pl_bridge.py`: Budget/Actual revenue via volume+price; GP = Rev − COGS (std-cost based)
- Tests `t3`; SQLite tables; Streamlit **P&L Bridge** page
- `run_pipeline.py` order: …09 → **10** → tests → 05 → 04

### Limits
- Product-level MixEffect = 0 (SKU grain); see engine `PVM_Bridge` for existing mix analytics
- No fixed overhead / EBITDA
- Yield variance at standard VC only (no purchase-price variance)
