"""Compare inventory fulfillment under SAME_PERIOD_SHIP = 1 vs 0.

Uses existing FactProduction monthly goods + FactDemand firm demand,
re-simulates roll-forward only (does not mutate baseline outputs).
Opening stock is seeded from FactInventorySnapshot when present.

Writes final/Sensitivity_SamePeriodShip.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT, FIN = ROOT / "output", ROOT / "final"


def rollforward(good: pd.DataFrame, firm: pd.DataFrame, same_period_ship: int) -> pd.DataFrame:
    """good: PeriodKey, ProductID, GoodProduction; firm: PeriodKey, ProductID, FirmDemand"""
    periods = sorted(good.PeriodKey.astype(str).unique())
    products = sorted(good.ProductID.astype(str).unique())
    gmap = good.set_index(["PeriodKey", "ProductID"])["GoodProduction"].to_dict()
    fmap = firm.set_index(["PeriodKey", "ProductID"])["FirmDemand"].to_dict()

    opening = {}
    inv_path = OUT / "FactInventorySnapshot.csv"
    if inv_path.exists():
        inv = pd.read_csv(inv_path)
        inv["PeriodKey"] = inv.PeriodKey.astype(str)
        inv["ProductID"] = inv.ProductID.astype(str)
        first_per = periods[0]
        sub = inv[inv.PeriodKey == first_per]
        for p in products:
            rows = sub[sub.ProductID == p]
            if len(rows) and "OpeningInventory" in rows.columns:
                opening[p] = int(rows.OpeningInventory.iloc[0])
            else:
                opening[p] = int(round(float(gmap.get((first_per, p), 0)) * 0.05))
    else:
        for p in products:
            opening[p] = int(round(float(gmap.get((periods[0], p), 0)) * 0.05))

    rows = []
    for period in periods:
        for p in products:
            gp = int(gmap.get((period, p), 0))
            fd = int(fmap.get((period, p), 0))
            avail = opening[p] + gp if same_period_ship else opening[p]
            ship = min(fd, avail)
            close = opening[p] + gp - ship
            lost = max(0, fd - ship)
            rows.append(dict(
                PeriodKey=period, ProductID=p, SamePeriodShip=same_period_ship,
                Opening=opening[p], GoodProduction=gp, FirmDemand=fd,
                Shipments=ship, Closing=close, LostVsDemand=lost,
            ))
            opening[p] = close
    return pd.DataFrame(rows)


def main():
    prod = pd.read_csv(OUT / "FactProduction.csv")
    prod["PeriodKey"] = prod.DateKey.astype(str).str[:6]
    good = (
        prod.groupby(["PeriodKey", "ProductID"], as_index=False)["GoodUnits"]
        .sum()
        .rename(columns={"GoodUnits": "GoodProduction"})
    )
    dem = pd.read_csv(OUT / "FactDemand.csv")
    firm = dem[dem.DemandType == "Firm"][["PeriodKey", "ProductID", "DemandUnits"]].rename(
        columns={"DemandUnits": "FirmDemand"}
    )
    firm["PeriodKey"] = firm.PeriodKey.astype(str)
    firm["ProductID"] = firm.ProductID.astype(str)
    good["PeriodKey"] = good.PeriodKey.astype(str)
    good["ProductID"] = good.ProductID.astype(str)

    summaries = []
    detail = []
    for flag in (1, 0):
        df = rollforward(good, firm, flag)
        detail.append(df)
        summaries.append(dict(
            SamePeriodShip=flag,
            Label="Same-period ship allowed" if flag == 1 else "Opening-only ship (no same-period production)",
            TotalShipments=int(df.Shipments.sum()),
            TotalLostVsDemand=int(df.LostVsDemand.sum()),
            EndingInventory=int(df.groupby("ProductID").Closing.last().sum()),
            ProductMonthsShort=int((df.LostVsDemand > 0).sum()),
        ))

    summ = pd.DataFrame(summaries)
    summ["LostDelta_vs_baseline"] = summ.TotalLostVsDemand - summ.loc[summ.SamePeriodShip == 1, "TotalLostVsDemand"].iloc[0]
    summ.to_csv(FIN / "Sensitivity_SamePeriodShip.csv", index=False)
    pd.concat(detail, ignore_index=True).to_csv(FIN / "Sensitivity_SamePeriodShip_Detail.csv", index=False)
    print(summ.to_string(index=False))
    print(f"\nWrote {FIN / 'Sensitivity_SamePeriodShip.csv'}")


if __name__ == "__main__":
    main()
