# Process & Causal Map — North Valley Dairy (synthetic)

**Companion to:** `docs/DECISION_BRIEF.md`  
**Version:** 1.9.0.1  

---

## 1. Process map (happy path)

```text
Firm demand / orders (retail & distributors)
        ↓
Production planning & sequence (SKU on capable line)
        ↓
Scheduled run (pasteurizer → filler / cup / pack)
        ↓
Actual production (good / scrap / rework flags)
        ↓
Quality release (lab hold may delay — narrative)
        ↓
Cold store receipt & allocation (0–4°C)
        ↓
Shipment / dispatch dock
        ↓
Recognized volume → Net revenue → Contribution margin
```

**Side events (interrupt the path)**

| Event | Typical effect |
|-------|----------------|
| CIP / sanitation | Planned availability loss |
| SKU changeover | Planned availability loss |
| Filler / pasteurizer breakdown | Unplanned availability loss |
| Raw milk / material shortage | Unplanned availability loss |
| Micro-stops / speed loss | Performance loss |
| Quality hold / lab reject | Quality loss; may block ship |

---

## 2. OEE loss tree (operational depth)

```text
OEE loss (vs ideal)
├── Availability
│   ├── Failure (filler, pasteurizer, utilities)
│   ├── CIP / sanitation
│   ├── Changeover (allergen / pack size)
│   └── Material shortage (raw milk, packaging)
├── Performance
│   ├── Speed loss
│   └── Micro-stops
└── Quality
    ├── Scrap / reject
    ├── Rework (limited in dairy)
    └── Hold (not yet released)
```

**Dairy rule of thumb in this portfolio**

- “Recovery” means **overtime, extra run, or divert to another capable line**  
- It does **not** mean turning spoiled milk back into saleable fresh SKU  

---

## 3. Causal chain (hypothesis under study)

```text
Unplanned or planned stop / slow running
        ↓
Fewer good packs (vs plan)
        ↓
Coverage gap vs firm demand
        ↓
┌───────────────┬─────────────────┬──────────────────┐
│ Cold inventory│ Recovery effort │ Alternate filler │
│ (opening FG)  │ (OT / extra run) │ (if capable+slack)│
└───────┬───────┴────────┬────────┴────────┬─────────┘
        ↓                ↓                 ↓
   Partial fill     Costly partial     Partial fill
        └────────────────┬─────────────────┘
                         ↓
              Residual unmet demand (modeled lost sales)
                         ↓
         Residual CM exposure  vs  Protected CM − recovery cost
```

This is a **structured scenario chain**, not a statistically identified causal effect from real plant data.

---

## 4. Confounders (why OEE% alone misleads)

| Factor | How it confuses “OEE → $” |
|--------|---------------------------|
| Demand spike / promo | Gap grows even if OEE stable |
| Product mix | High-CM SKU loss hurts more than low-CM |
| Planned CIP | Expected loss; not a “failure crisis” |
| Line capability | Some SKUs cannot divert |
| Quality release lag | Good units exist but cannot ship yet |
| Inventory policy | High buffer hides OEE loss in the short run |
| Seasonality | Yogurt/milk patterns change coverage |
| Same-period ship rule | Production may not be dispatchable in-period |

---

## 5. Baseline vs action (conceptual)

| World | Process meaning |
|-------|-----------------|
| **Baseline** | Accept residual shortfall after normal inventory policy; no extra OT/divert campaign |
| **Action** | Spend recovery effort and/or alternate-line time to convert gap into shipments |

**Modeled benefit** ≈ extra protected CM minus incremental effort cost (and optional holding proxy).

---

## 6. Link to existing pipeline tables

| Process step | Primary artifacts |
|--------------|-------------------|
| Demand | `FactDemand`, firm demand on Impact |
| Run / OEE | `FactProduction`, `FactOEE_Run`, `FactDowntime` |
| Inventory | `FactInventorySnapshot`, Impact absorption columns |
| Capability | `Bridge_ProductLineCapability` |
| Financial outcome | Impact CM fields, `PVM_Bridge`, executive summary |
| Decision ranking | `Opportunity_Prioritization`, dashboard product page |

---

## 7. What this map is for

- Interview / stakeholder story before opening charts  
- Guardrail against over-claiming causality  
- Checklist for future data (quality release time, backlog, recovery by reason)  
