# Changelog — v1.8.5

## Capacity-aware ranking + downtime Pareto

1. **CM per constrained hour** on Decision_Action_Comparison:
   - MitigationHours = recovered/primary_rate + subst/alt_rate
   - ProtectedCM_per_ConstrainedHour, NetCM_per_ConstrainedHour
2. Dashboard Decision page: dual rank ($ value vs $/hour)
3. **08_downtime_reason_pareto.py** → Downtime_Reason_Pareto.csv (descriptive)
4. No change to recovery allocation math (still global RECOVERY_FRAC)
