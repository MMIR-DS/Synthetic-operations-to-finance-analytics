#!/usr/bin/env python3
"""Orchestrate the full OEE → Revenue → CM pipeline (regenerable end-to-end).

Usage:
  python run_pipeline.py              # full run (generate → analytics → tests → sqlite → exec pack)
  python run_pipeline.py --skip-tests
  python run_pipeline.py --from 07    # start at step id/prefix
  python run_pipeline.py --list

Order matches README v1.8.7+: 01 → 02 → 03 → 06 → 07 → 08 → 09 → 10 → tests → 05 → 04
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (step_id, script relative to ROOT, description)
STEPS = [
    ("01", "01_generate_synthetic_data_fixed.py", "Generate synthetic dairy facts + dims"),
    ("02", "02_oee_revenue_cm_engine_fixed.py", "OEE / gap / CM engine + integrity"),
    ("03", "03_sensitivity_recovery.py", "RECOVERY_FRAC sensitivity"),
    ("06", "06_sensitivity_same_period_ship.py", "SAME_PERIOD_SHIP sensitivity"),
    ("07", "07_baseline_vs_action.py", "Baseline vs action + risk-adjusted CM"),
    ("08", "08_downtime_reason_pareto.py", "Downtime reason Pareto"),
    ("09", "09_finance_decision_artifacts.py", "P_REALIZE sens, budget recon, decision checks"),
    ("10", "10_pl_bridge.py", "P&L Bridge Budget→Actual GP"),
    ("t1", "tests/test_fixture_two_period.py", "Fixture identity tests"),
    ("t2", "tests/test_decision_baseline_action.py", "Decision baseline/action tests"),
    ("t3", "tests/test_pl_bridge.py", "P&L Bridge identity tests"),
    ("05", "05_build_sqlite_with_keys.py", "SQLite PK/FK database"),
    ("04", "04_build_executive_pack.py", "Executive case study + report (after 07–09)"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run North Valley Dairy OEE→CM pipeline")
    p.add_argument("--skip-tests", action="store_true", help="Skip t1/t2 test steps")
    p.add_argument(
        "--from",
        dest="from_step",
        default=None,
        metavar="ID",
        help="Start from step id (e.g. 07, t1, 05)",
    )
    p.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help="Run only these step ids",
    )
    p.add_argument("--list", action="store_true", help="List steps and exit")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    return p.parse_args()


def select_steps(args: argparse.Namespace):
    steps = list(STEPS)
    if args.skip_tests:
        steps = [s for s in steps if not s[0].startswith("t")]
    if args.only:
        want = set(args.only)
        steps = [s for s in steps if s[0] in want]
        missing = want - {s[0] for s in steps}
        if missing:
            raise SystemExit(f"Unknown step id(s): {sorted(missing)}")
    if args.from_step:
        ids = [s[0] for s in steps]
        if args.from_step not in ids:
            raise SystemExit(f"--from {args.from_step} not in selected steps: {ids}")
        idx = ids.index(args.from_step)
        steps = steps[idx:]
    return steps


def run_step(step_id: str, script: str, desc: str, dry_run: bool) -> None:
    path = ROOT / script
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    cmd = [sys.executable, str(path)]
    print(f"\n{'='*60}")
    print(f"[{step_id}] {desc}")
    print(f"  → {' '.join(cmd)}")
    print(f"{'='*60}")
    if dry_run:
        return
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(ROOT))
    dt = time.perf_counter() - t0
    if proc.returncode != 0:
        raise SystemExit(
            f"FAILED step [{step_id}] {script} (exit {proc.returncode}) after {dt:.1f}s"
        )
    print(f"OK [{step_id}] in {dt:.1f}s")


def main() -> None:
    args = parse_args()
    steps = select_steps(args)
    if args.list:
        for sid, script, desc in steps:
            print(f"  {sid:3}  {script:45}  {desc}")
        return

    print(f"Pipeline root: {ROOT}")
    print(f"Steps to run: {[s[0] for s in steps]}")
    t0 = time.perf_counter()
    for sid, script, desc in steps:
        run_step(sid, script, desc, args.dry_run)
    if not args.dry_run:
        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETE in {time.perf_counter() - t0:.1f}s")
        print("Outputs: final/  output/  final/oee_revenue_cm_model.db")
        print("Dashboard: streamlit run dashboard/app.py")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
