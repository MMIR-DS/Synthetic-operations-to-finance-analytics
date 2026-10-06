# Changelog — v1.7

## Financial / ops realism

1. **Inventory holding cost** — monthly `AvgInventory × VC × (WACC/12)` on Impact; summary fields `inventory_holding_cost`, `net_cm_after_holding`.
2. **Stepped recovery cost** — Tier1/2/3 ($2 / $7 / $14 by default) on mitigated units as fractions of gross gap; configurable via ModelAssumptions. `FLAT` still supported.

## Config
New ModelAssumptions: `HOLDING_COST_ANNUAL_WACC`, `RECOVERY_COST_MODE`, `RECOVERY_TIER*_FRAC/COST`.
