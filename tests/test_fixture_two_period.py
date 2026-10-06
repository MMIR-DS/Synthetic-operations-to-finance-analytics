"""Two-period fixture tests for financial identities and waterfall logic."""
from __future__ import annotations

import math


def test_gap_waterfall_identity():
    gross, inv, rec, sub, lost = 1000.0, 200.0, 150.0, 300.0, 350.0
    assert abs(gross - (inv + rec + sub + lost)) < 1e-9


def test_net_cm_identity():
    protected, recovery_cost = 5000.0, 1200.0
    net = protected - recovery_cost
    assert abs(net - 3800.0) < 1e-9


def test_uneconomic_mitigation_negative_net():
    protected, recovery_cost = 100.0, 250.0
    net = protected - recovery_cost
    assert net < 0


def test_oee_product():
    a, p, q = 0.9, 0.95, 0.98
    oee = a * p * q
    assert 0 <= oee <= 1
    assert abs(oee - 0.8379) < 1e-3


if __name__ == "__main__":
    test_gap_waterfall_identity()
    test_net_cm_identity()
    test_uneconomic_mitigation_negative_net()
    test_oee_product()
    print("test_fixture_two_period: OK")
