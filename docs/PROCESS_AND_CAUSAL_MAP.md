# Process & Causal Map — North Valley Dairy (synthetic)

**Version:** 1.9.0.1 · Companion to `docs/DECISION_BRIEF.md`

## Happy path

```text
Firm demand → Planning → Scheduled run → Actual production
  → Quality release → Cold store → Shipment → Revenue → CM
```

## Side events

CIP, changeover, breakdown, material shortage → Availability loss  
Speed / micro-stops → Performance loss  
Scrap / hold → Quality loss

## Causal chain (modeled)

```text
Stop / slow run
  → Fewer good packs
  → Gap vs firm demand
  → Inventory | Recovery | Alternate line
  → Residual lost sales
  → CM exposure / Protected CM / Net opportunity
```

**Dairy note:** Recovery = OT / extra run / divert — **not** rework of spoiled milk.

## OEE

Run grain: A × P × Q; plant roll-up **time-weighted** by planned hours.
