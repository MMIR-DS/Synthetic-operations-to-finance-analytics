# v1.2 — Portfolio model corrections

## Fixed

### 1. Opening inventory was incorrectly represented as closing-period absorbable inventory
The demand-gap waterfall now uses `OpeningAvailableInventory` to absorb the current-period production shortfall. Closing inventory remains a residual balance and is never reused as same-period supply.

### 2. Same-line substitution
`AltLineID` is now selected only from a capable line different from the primary line. Products without a distinct alternate line have no substitution path.

### 3. Recovery and substitution are separated
Generic recovery no longer depends on the existence of an alternate production line. Alternate-line capability is used only for substitution.

### 4. Sales rounding drift
Sales transactions are allocated with integer multinomial allocation, guaranteeing exact reconciliation between `FactSales.Units` and roll-forward `Shipments`.

### 5. Validation
Added regression tests for opening-inventory treatment and distinct alternate-line logic. The corrected run passes all fixture tests and all integrity checks.

## Corrected FY2024 baseline outputs

- Time-weighted OEE: 83.98%
- Gross production shortfall: 134,788 EA
- Opening inventory absorbed: 20,516 EA
- Recovered units: 22,854 EA
- Substituted units: 34,903 EA
- Potential lost sales: 56,515 EA
- CM exposure: $1.615M
- Protected CM: $1.773M
- Recovery cost: $0.462M
- Net CM opportunity: $1.311M

All figures are synthetic model outputs under the documented assumptions.
