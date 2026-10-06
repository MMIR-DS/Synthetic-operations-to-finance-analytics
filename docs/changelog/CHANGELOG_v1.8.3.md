# Changelog — v1.8.3

## Baseline vs Action + risk-adjusted benefit

- `07_baseline_vs_action.py`
  - Baseline: inventory absorption only
  - Action: recovery + substitution path from FactImpact
  - Δ lost units, Δ CM exposure avoided, Δ Net operational CM
  - `Expected_RiskAdjustedCM = max(0, Δ Net) × P_REALIZE`
- `P_REALIZE=0.65` in ModelAssumptions (assumption, not fitted)
- Outputs: `Decision_Action_Comparison.csv`, `Decision_Action_Summary.json`
