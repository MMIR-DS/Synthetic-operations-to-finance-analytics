# COGS components & shallow BOM — North Valley Dairy

Portfolio release: **1.9.0.1** · Cost model: **1.9.0**

**Version:** 1.9.0.1  
**Level:** L1 cost split + shallow 1-level BOM (not full MRP)

---

## Design choice

| Keep | Change |
|------|--------|
| `StandardVariableCost` total (engine CM unchanged) | Split into **Raw milk / Packaging / Processing energy / Other** |
| Model-USD price scale (readable $1.12M opportunity) | **Shares** calibrated to public dairy structure |
| CM = Price − VC | Identity: `VC = Raw + Pack + Process + Other` |

Full multi-level BOM, ingredient inventory, and purchasing are **out of scope**.

---

## Public benchmarks used (indicative)

| Benchmark | Approximate fact | Use in model |
|-----------|------------------|--------------|
| USDA ERS 2024 whole milk | Farm value ~**49%** of retail gallon (~$1.97 of ~$3.98) | Raw milk **share of price** for fluid SKUs ~41–46% |
| Industry fluid processing | Raw milk is the **majority** of plant variable cost | Raw ~**65–70% of VC** for fresh milk SKUs |
| Cheese / butter | Higher processing / cream intensity; farm share of retail varies (butter high, cheddar lower) | Lower raw/price for cheese; higher process $ |
| Yogurt | More packaging + culture vs fluid | Higher pack share of VC |

**Disclaimer:** Synthetic **model-USD** levels are not a quote of any plant’s actual COGS. Shares are **illustrative** and directionally consistent with public farm-to-retail structure.

---

## Component definitions (variable only)

| Field | Meaning |
|-------|---------|
| `RawMilkCost` | Farm/co-op milk solids allocated per retail unit |
| `PackagingCost` | Carton, cup, tub, label (primary pack) |
| `ProcessingEnergyCost` | Pasteurization, CIP energy, filling utilities (proxy) |
| `OtherVariableCost` | Culture, salt, minor ingredients, misc. variable |
| `StandardVariableCost` | Sum of the four (managerial VC for CM) |

**Not included in VC:** plant depreciation, allocated SG&A, retail margin, distribution (cost-to-serve later).

---

## Example shares (P1 Full cream 1L)

| Component | Model $ | % of price | % of VC |
|-----------|--------:|----------:|--------:|
| Raw milk | 43 | 43% | 69% |
| Packaging | 9 | 9% | 15% |
| Processing energy | 6 | 6% | 10% |
| Other | 4 | 4% | 6% |
| **VC total** | **62** | **62%** | 100% |
| **CM** | **38** | **38%** | — |

---

## Shallow BOM (`Bridge_BOM.csv`)

| ComponentID | Role |
|-------------|------|
| RAW-MILK | Liters (or milk-equivalent) per pack |
| PACK-PRIMARY | 1 primary package per unit |
| CULTURE-AUX | Yogurt/cheese auxiliaries (maps to OtherVariableCost) |

Qty is educational; **costing still uses DimProduct money fields** (single source for CM).

---

## Link to decision metrics

```text
CM/unit = StandardPrice − StandardVariableCost
Protected CM = mitigated units × CM/unit   (unchanged)
Recovery cost = stepped OT/divert cost     (extra; not inside VC)
```

OT recovery is **not** double-counted inside ProcessingEnergyCost.

---

## Files

- `output/DimProduct.csv` — component columns + shares  
- `output/Bridge_BOM.csv` — shallow recipe  
- Engine still reads **StandardVariableCost** for CM  
