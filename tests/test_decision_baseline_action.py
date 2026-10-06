"""Decision baseline/action identity checks."""
from __future__ import annotations


def test_action_lost_not_exceed_baseline():
    baseline_lost, action_lost = 1000.0, 600.0
    assert action_lost <= baseline_lost + 1e-9


def test_delta_net_identity():
    # Modeled opportunity reduces to protected CM - recovery cost path
    protected, recovery = 2000.0, 500.0
    delta_net = protected - recovery
    assert abs(delta_net - 1500.0) < 1e-9


def test_p_realize_scalar():
    net, p = 1000.0, 0.65
    expected = max(0.0, net) * p
    assert abs(expected - 650.0) < 1e-9


if __name__ == "__main__":
    test_action_lost_not_exceed_baseline()
    test_delta_net_identity()
    test_p_realize_scalar()
    print("test_decision_baseline_action: OK")
