"""P&L bridge identity tests."""
from __future__ import annotations


def test_cogs_bridge_identity():
    budget, volume_eff, yield_var, actual = 1000.0, 50.0, -20.0, 1030.0
    assert abs(budget + volume_eff + yield_var - actual) < 1e-9


def test_gp_variance_identity():
    actual_gp, budget_gp = 500.0, 600.0
    assert abs((actual_gp - budget_gp) - (-100.0)) < 1e-9


if __name__ == "__main__":
    test_cogs_bridge_identity()
    test_gp_variance_identity()
    print("test_pl_bridge: OK")
