"""Validate P&L Bridge outputs (v1.9.0)."""
from pathlib import Path
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIN = ROOT / "final"

def test_pl_bridge_files_exist():
    assert (FIN / "PL_Bridge_Detail.csv").exists()
    assert (FIN / "PL_Bridge_Summary.csv").exists()
    assert (FIN / "PL_Bridge_Summary.json").exists()

def test_revenue_bridge_identity():
    d = pd.read_csv(FIN / "PL_Bridge_Detail.csv")
    err = (d.BudgetRevenue + d.VolumeEffect + d.MixEffect + d.PriceEffect - d.ActualRevenue).abs().max()
    assert err < 1.0, err

def test_cogs_bridge_identity():
    d = pd.read_csv(FIN / "PL_Bridge_Detail.csv")
    err = (d.BudgetCOGS + d.VolumeCOGSEffect + d.YieldVariance - d.ActualCOGS).abs().max()
    assert err < 1.0, err

def test_gp_identity():
    d = pd.read_csv(FIN / "PL_Bridge_Detail.csv")
    err = (d.ActualRevenue - d.ActualCOGS - d.ActualGP).abs().max()
    assert err < 1.0, err

def test_summary_rollup():
    d = pd.read_csv(FIN / "PL_Bridge_Detail.csv")
    s = pd.read_csv(FIN / "PL_Bridge_Summary.csv")
    for col in ["BudgetRevenue", "ActualRevenue", "BudgetGP", "ActualGP"]:
        a = d.groupby("PeriodKey")[col].sum()
        b = s.set_index("PeriodKey")[col]
        assert (a - b).abs().max() < 1.0, col

if __name__ == "__main__":
    test_pl_bridge_files_exist()
    test_revenue_bridge_identity()
    test_cogs_bridge_identity()
    test_gp_identity()
    test_summary_rollup()
    print("All P&L Bridge tests passed.")
    sys.exit(0)
