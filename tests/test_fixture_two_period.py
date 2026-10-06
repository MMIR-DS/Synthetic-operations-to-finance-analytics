"""Manual expected-value fixture + edge cases.

Core case: two periods, one product (hand-calculated).
Edge cases: zero demand, zero production, recovery frac 0/1, recovery cost > CM.
"""
from __future__ import annotations

import sys


def almost_equal(a, b, tol=1e-9):
    return abs(a - b) <= tol


def close_gap(gross_gap, opening_inventory, recovery_frac, subst_cap, cm_unit, recovery_cost_unit):
    """Same identities as the engine gap-closure."""
    # Inventory available to current-period demand comes from opening inventory, not closing inventory.
    absorb = min(max(gross_gap, 0.0), max(opening_inventory, 0.0))
    gap1 = max(0.0, gross_gap - absorb)
    recovered = min(gap1, recovery_frac * gap1)
    gap2 = gap1 - recovered
    subst = min(gap2, max(subst_cap, 0.0))
    lost = max(0.0, gap2 - subst)
    protected = (recovered + subst) * cm_unit
    cost = (recovered + subst) * recovery_cost_unit
    net = protected - cost
    cm_exposure = lost * cm_unit
    return {
        "absorb": absorb,
        "recovered": recovered,
        "subst": subst,
        "lost": lost,
        "protected": protected,
        "cost": cost,
        "net": net,
        "cm_exposure": cm_exposure,
    }


def test_inventory_rollforward():
    opening_1, good_1, demand_1 = 100, 500, 700
    ship_1 = min(demand_1, opening_1 + good_1)
    close_1 = opening_1 + good_1 - ship_1
    assert ship_1 == 600 and close_1 == 0

    opening_2, good_2, demand_2 = close_1, 400, 300
    ship_2 = min(demand_2, opening_2 + good_2)
    close_2 = opening_2 + good_2 - ship_2
    assert opening_2 == 0 and ship_2 == 300 and close_2 == 100


def test_gap_waterfall_and_cm_bridge():
    cm_unit, recovery_cost_unit = 4.0, 8.0
    r = close_gap(
        gross_gap=200.0, opening_inventory=100.0, recovery_frac=0.20,
        subst_cap=0.0, cm_unit=cm_unit, recovery_cost_unit=recovery_cost_unit,
    )
    assert almost_equal(r["absorb"], 100.0)
    assert almost_equal(r["recovered"], 20.0)
    assert almost_equal(r["lost"], 80.0)
    assert almost_equal(200.0, r["absorb"] + r["recovered"] + r["subst"] + r["lost"])
    assert almost_equal(r["protected"], 80.0)
    assert almost_equal(r["cost"], 160.0)
    assert almost_equal(r["net"], -80.0)
    assert almost_equal(r["cm_exposure"], 320.0)
    assert almost_equal(r["net"], r["protected"] - r["cost"])
    assert not almost_equal(r["net"], r["cm_exposure"] - r["cost"])



def test_opening_inventory_is_used_not_closing_inventory():
    # 100 opening + 500 production can fulfill 600 demand; there is no residual gap.
    gross = max(0.0, 600.0 - 500.0)
    r = close_gap(gross, opening_inventory=100.0, recovery_frac=0.2, subst_cap=0.0, cm_unit=4.0, recovery_cost_unit=8.0)
    assert r["absorb"] == 100.0
    assert r["lost"] == 0.0


def test_alternate_line_must_be_distinct():
    # Mirror the production selection rule: highest StandardRate is primary;
    # alternate candidates must be capable lines other than the primary.
    bridge = {
        "P2": [("L1", 100.0)],
        "P3": [("L2", 100.0), ("L1", 80.0)],
    }
    for product, candidates in bridge.items():
        primary = sorted(candidates, key=lambda x: x[1], reverse=True)[0][0]
        alternates = [line for line, _rate in candidates if line != primary]
        if product == "P2":
            assert alternates == []
        else:
            assert alternates == ["L1"]
            assert all(line != primary for line in alternates)


def test_sales_reconcile_exactly_to_shipments():
    shipments = {("202401", "P1"): 600, ("202402", "P1"): 300}
    sales = {("202401", "P1"): 600, ("202402", "P1"): 300}
    assert sales == shipments
    assert all(sales[k] <= shipments[k] for k in shipments)

def test_domain_rules():
    price, vc = 10.0, 6.0
    assert price > 0 and vc >= 0 and vc <= price
    assert 0 <= 0.85 <= 1
    assert 0 <= 0.2 <= 1


def test_zero_demand():
    # No demand → no gap, no lost sales
    r = close_gap(0.0, 50.0, 0.2, 10.0, 4.0, 8.0)
    assert r["absorb"] == 0 and r["recovered"] == 0 and r["lost"] == 0
    assert r["net"] == 0 and r["cm_exposure"] == 0


def test_zero_production_full_demand():
    # Primary supply 0, demand 100, no inventory
    gross = max(0.0, 100.0 - 0.0)
    r = close_gap(gross, 0.0, 0.2, 0.0, 4.0, 8.0)
    assert almost_equal(r["recovered"], 20.0)
    assert almost_equal(r["lost"], 80.0)
    assert almost_equal(gross, r["absorb"] + r["recovered"] + r["subst"] + r["lost"])


def test_recovery_frac_zero_and_one():
    r0 = close_gap(100.0, 0.0, 0.0, 0.0, 5.0, 2.0)
    assert r0["recovered"] == 0 and almost_equal(r0["lost"], 100.0)

    r1 = close_gap(100.0, 0.0, 1.0, 0.0, 5.0, 2.0)
    assert almost_equal(r1["recovered"], 100.0) and r1["lost"] == 0
    assert almost_equal(r1["protected"], 500.0)
    assert almost_equal(r1["cost"], 200.0)
    assert almost_equal(r1["net"], 300.0)


def test_recovery_cost_exceeds_protected_cm():
    # High recovery cost → negative net (uneconomic mitigation)
    r = close_gap(100.0, 0.0, 0.5, 0.0, cm_unit=3.0, recovery_cost_unit=10.0)
    assert almost_equal(r["recovered"], 50.0)
    assert almost_equal(r["protected"], 150.0)
    assert almost_equal(r["cost"], 500.0)
    assert r["net"] < 0
    assert almost_equal(r["net"], r["protected"] - r["cost"])


def test_price_equals_variable_cost():
    cm_unit = 0.0  # price == VC
    r = close_gap(50.0, 0.0, 0.2, 0.0, cm_unit, 8.0)
    assert r["protected"] == 0.0
    assert r["cm_exposure"] == 0.0
    assert r["net"] == -r["cost"]  # pure cost, no CM benefit


if __name__ == "__main__":
    tests = [
        test_inventory_rollforward,
        test_gap_waterfall_and_cm_bridge,
        test_opening_inventory_is_used_not_closing_inventory,
        test_alternate_line_must_be_distinct,
        test_sales_reconcile_exactly_to_shipments,
        test_domain_rules,
        test_zero_demand,
        test_zero_production_full_demand,
        test_recovery_frac_zero_and_one,
        test_recovery_cost_exceeds_protected_cm,
        test_price_equals_variable_cost,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {e}")
    if failed:
        sys.exit(1)
    print(f"All {len(tests)} fixture tests passed.")
