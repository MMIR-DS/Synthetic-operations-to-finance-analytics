"""Downtime reason Pareto — operational depth (not a $ causal model).

Joins FactDowntime to DimDowntimeReason; reports minutes and share by reason.
Does not change recovery allocation (still global RECOVERY_FRAC).
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT, FIN = ROOT / "output", ROOT / "final"

def main():
    dt = pd.read_csv(OUT / "FactDowntime.csv")
    reason = pd.read_csv(OUT / "DimDowntimeReason.csv")
    m = dt.merge(reason, on="DowntimeReasonID", how="left")
    if "DurationMinutes" not in m.columns:
        for c in m.columns:
            if "Duration" in c or "Minute" in c:
                m = m.rename(columns={c: "DurationMinutes"})
                break
    key_cols = [c for c in ["DowntimeReasonID", "Reason", "Category", "PlannedUnplanned", "LossType"] if c in m.columns]
    event_col = "DowntimeEventID" if "DowntimeEventID" in m.columns else m.columns[0]
    g = (
        m.groupby(key_cols, dropna=False)
        .agg(Events=(event_col, "count"), Minutes=("DurationMinutes", "sum"))
        .reset_index()
    )
    total = g.Minutes.sum()
    g["ShareOfMinutes"] = (g.Minutes / total).round(4) if total else 0.0
    g = g.sort_values("Minutes", ascending=False)
    g.to_csv(FIN / "Downtime_Reason_Pareto.csv", index=False)
    summary = {
        "total_minutes": float(total),
        "top_reason": g.iloc[0].Reason if len(g) and "Reason" in g.columns else None,
        "top_share": float(g.iloc[0].ShareOfMinutes) if len(g) else None,
        "note": "Descriptive Pareto only; recovery rates are not yet reason-specific",
    }
    (FIN / "Downtime_Reason_Pareto_Summary.json").write_text(json.dumps(summary, indent=2))
    print(g.head(8).to_string(index=False))
    print("Wrote", FIN / "Downtime_Reason_Pareto.csv")

if __name__ == "__main__":
    main()
