# COGS and shallow BOM

Portfolio **1.9.0+**

## Variable cost split

`StandardVariableCost` = RawMilkCost + PackagingCost + ProcessingEnergyCost + OtherVariableCost

Identity holds at product level (max deviation 0.0 on reference run).

## Shallow BOM

`Bridge_BOM` / `FactBOMUsage`: one-level components (raw milk, packaging, process energy, other).

Cheese uses higher raw-milk quantity per unit (concentration); yogurt may include culture/auxiliary lines.

## P&L bridge

`FactCOGSVariance` / `10_pl_bridge.py`:

BudgetCOGS + VolumeCOGSEffect + YieldVariance = ActualCOGS

MixEffect = 0 at SKU grain (documented limit).

CM remains the intervention metric; GP bridge is plan-to-actual context.
