"""Shared recovery cost model (STEPPED / FLAT) used by engine and sensitivity."""
from __future__ import annotations

from typing import Mapping


def stepped_recovery_cost(
    recovered_units: float,
    gross_gap: float,
    *,
    tier1_frac: float = 0.05,
    tier2_frac: float = 0.15,
    tier1_cost: float = 2.0,
    tier2_cost: float = 7.0,
    tier3_cost: float = 14.0,
) -> float:
    """Allocate recovered units into gap-fraction tiers; price each band."""
    if recovered_units <= 0 or gross_gap <= 0:
        return 0.0
    g = float(gross_gap)
    r = float(recovered_units)
    b1 = min(r, tier1_frac * g)
    rem = r - b1
    b2 = min(rem, max(0.0, (tier2_frac - tier1_frac) * g))
    b3 = rem - b2
    return b1 * tier1_cost + b2 * tier2_cost + b3 * tier3_cost


def recovery_cost_for_units(
    recovered_units: float,
    gross_gap: float,
    assumptions: Mapping[str, float | str],
) -> float:
    mode = str(assumptions.get("RECOVERY_COST_MODE", "STEPPED")).upper()
    if mode == "FLAT":
        unit = float(assumptions.get("RECOVERY_COST_UNIT", 8.0))
        return float(recovered_units) * unit
    return stepped_recovery_cost(
        recovered_units,
        gross_gap,
        tier1_frac=float(assumptions.get("RECOVERY_TIER1_FRAC", 0.05)),
        tier2_frac=float(assumptions.get("RECOVERY_TIER2_FRAC", 0.15)),
        tier1_cost=float(assumptions.get("RECOVERY_TIER1_COST", 2.0)),
        tier2_cost=float(assumptions.get("RECOVERY_TIER2_COST", 7.0)),
        tier3_cost=float(assumptions.get("RECOVERY_TIER3_COST", 14.0)),
    )
