"""Verify baseline vs action inventory consistency and P_REALIZE sensitivity."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIN = ROOT / "final"

def test_action_lost_le_baseline_inventory_only():
    comp = pd.read_csv(FIN / "Decision_Action_Comparison.csv")
    # Baseline_LostUnits should equal gap after inventory
    assert (comp.Action_LostUnits <= comp.Baseline_LostUnits + 1e-6).all()

def test_delta_net_equals_action_net():
    comp = pd.read_csv(FIN / "Decision_Action_Comparison.csv")
    assert (comp.Delta_NetOperationalCM - comp.Action_NetCMOpportunity).abs().max() < 0.05

def test_p_realize_sensitivity_scalar():
    sens = pd.read_csv(FIN / "Sensitivity_P_Realize.csv")
    net = float(sens.Delta_NetOperationalCM.iloc[0])
    for _, r in sens.iterrows():
        assert abs(max(0.0, net) * float(r.P_REALIZE) - float(r.Expected_RiskAdjustedCM)) < 0.5

def test_decision_logic_checks_json():
    d = json.loads((FIN / "decision_logic_checks.json").read_text())
    assert d["action_lost_le_baseline_lost"] is True

if __name__ == "__main__":
    test_action_lost_le_baseline_inventory_only()
    test_delta_net_equals_action_net()
    test_p_realize_sensitivity_scalar()
    test_decision_logic_checks_json()
    print("All decision baseline/action tests passed.")
