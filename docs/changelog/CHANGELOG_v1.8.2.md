# Changelog — v1.8.2

## COGS depth (L1) + shallow BOM

- DimProduct: RawMilkCost, PackagingCost, ProcessingEnergyCost, OtherVariableCost
- Identity: StandardVariableCost = sum of components (CM engine unchanged)
- Bridge_BOM.csv: RAW-MILK, PACK-PRIMARY, CULTURE-AUX
- Cost *shares* aligned to public dairy structure (e.g. USDA ERS whole-milk farm share ~49% of retail as context); model-$ scale kept for portfolio readability
- docs/COGS_AND_BOM.md

No change to gap waterfall or NetCMOpportunity identities.
