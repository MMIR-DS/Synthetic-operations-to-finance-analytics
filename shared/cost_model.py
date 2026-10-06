"""Stepped / flat mitigation cost — single implementation for engine + sensitivity.

Tier bands are sized against ``gap_ref``. Canonical choice for this project:
**gross gap (pre–inventory absorption)**, matching the engine baseline so that
sensitivity at RECOVERY_FRAC=baseline reproduces engine RecoveryCost / NetCM.
"""
from __future__ import annotations


def mitigation_cost(
    units: float,
    gap_ref: float,
    *,
    mode: str = "STEPPED",
    flat_unit_cost: float = 8.0,
    tier1_frac: float = 0.05,
    tier1_cost: float = 2.0,
    tier2_frac: float = 0.15,
    tier2_cost: float = 7.0,
    tier3_cost: float = 14.0,
) -> float:
    """Cost of recovered + substituted units.

    Parameters
    ----------
    units:
        Mitigated volume (recovery + substitution).
    gap_ref:
        Denominator for tier caps. Use **GrossGap** (pre-absorption) for
        consistency with the engine.
    mode:
        ``STEPPED`` or ``FLAT``.
    """
    units = float(max(0.0, units))
    if units <= 0:
        return 0.0
    if str(mode).upper() != "STEPPED":
        return units * float(flat_unit_cost)
    gap_ref = float(max(gap_ref, units, 1e-9))
    t1_cap = max(0.0, float(tier1_frac)) * gap_ref
    t2_cap = max(float(tier2_frac), float(tier1_frac)) * gap_ref
    remaining = units
    cost = 0.0
    take = min(remaining, t1_cap)
    cost += take * float(tier1_cost)
    remaining -= take
    take = min(remaining, max(0.0, t2_cap - t1_cap))
    cost += take * float(tier2_cost)
    remaining -= take
    cost += remaining * float(tier3_cost)
    return cost
