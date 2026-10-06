# Changelog — v1.3

## Analytical / validation polish

- Updated engine version metadata and module header to **v1.3**.
- Removed the obsolete ±2-unit sales validation tolerance; sales are now required to be ≤ firm demand with **zero tolerance**.
- Documented that sales reconcile exactly to shipments in the generated synthetic dataset.
- Strengthened the alternate-line fixture test so its primary/alternate selection mirrors the production rule rather than using a special-case primary assignment.
- Added an explicit exact sales-to-shipment fixture test.
- Clarified that `NetCMOpportunity` is a **modeled mitigation-value metric**, not total company financial opportunity.
- Clarified `Production Gap` terminology for the demand/supply waterfall.

## Presentation layer

Added `04_build_executive_pack.py`, which creates:

- `final/EXECUTIVE_CASE_STUDY.md`
- `final/Executive_KPIs.csv`
- four presentation charts under `final/charts/`

The executive pack is presentation-only and does not introduce new analytical assumptions.

## Deferred to a future modeling release

Detailed changeover/setup-time capacity consumption for alternate-line substitution remains outside the current baseline model. The existing capability bridge retains setup-time data for future refinement; v1.3 does not pretend that setup time is fully modeled.
