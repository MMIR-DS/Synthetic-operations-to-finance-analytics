# Changelog — v1.8.6.1

## Verification + wording (response to v1.8.6 review)

- `final/decision_logic_checks.json` + `tests/test_decision_baseline_action.py`
  - Action lost ≤ baseline (inventory-only) lost
  - Δ Net = Action NetCMOpportunity
  - P_REALIZE sensitivity = scalar × portfolio net
- Wording: **assumption-based realization adjustment** (not expected plant benefit)
- No formula change to opportunity economics
