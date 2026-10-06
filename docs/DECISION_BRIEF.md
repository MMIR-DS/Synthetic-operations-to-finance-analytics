# Decision Brief — North Valley Dairy (synthetic)

Portfolio release: **1.9.0.1** · Decision-model baseline: **1.9.0**

**Document type:** Business design (before / above the data model)  
**Version:** 1.9.0.1  
**Status:** Portfolio decision framing — not an approved plant policy  

---

## 1. Decision to be made

**For each SKU–Period (and its primary line), which capacity intervention should planning choose** so that **expected realized contribution margin** is improved versus doing nothing, without breaking cold-chain and service constraints?

This is **not**: “What is total OEE?” or “What is company profit?”

---

## 2. Business owner

| Role | Responsibility |
|------|----------------|
| **Primary owner** | Production / Planning Manager (weekly) |
| **Consulted** | Cold-store logistics, Quality, Commercial (key SKU priorities) |
| **Informed** | Plant manager, FP&A (modeled $ only) |

---

## 3. Decision horizon and grain

| Item | Choice |
|------|--------|
| Horizon | **Model grain: calendar month × SKU**; intended decision cadence: weekly planning review with monthly modeled economics |
| Analytical grain | `PeriodKey × ProductID` (primary line as attribute) |
| Review cadence | End of week / start of next planning cycle |

---

## 4. Scope

**In scope**

- Fresh milk, yogurt, cheese, butter SKUs at **North Valley Dairy (synthetic)**  
- Primary filler / pack line capacity and **capable alternate lines**  
- Cold-store opening inventory as a buffer  
- Overtime / recovery effort and stepped recovery cost  
- Modeled CM exposure and mitigation value  

**Out of scope**

- Pricing and promotions design  
- Capex (new fillers, new cold rooms)  
- Full FEFO lot optimization  
- Multi-plant network design  
- Guaranteed P&L or cash forecast  

---

## 5. Available actions (catalog)

| Action ID | Action | Typical when |
|-----------|--------|----------------|
| A0 | **Do nothing** (baseline) | Gap small or recovery uneconomic |
| A1 | **Use cold-store buffer** (opening inventory) | Usable FG exists; still within shelf-life story |
| A2 | **Recover on primary line** (OT / speed / extra run) | Gap remains after buffer; recovery fraction applies |
| A3 | **Divert to alternate capable line** | Bridge capability + slack hours exist |
| A4 | **Accept shortfall** | Residual gap after A1–A3 |

The engine’s waterfall (inventory → recovery → substitution → residual) is the **quantitative skeleton** of A1–A4.  
A0 is the counterfactual reference for “value of intervention.”

---

## 6. Constraints

| Constraint | How it appears in the model |
|------------|----------------------------|
| Line time / rate | Primary supply, alternate slack ledger |
| Capability | `Bridge_ProductLineCapability` (SKU ↔ line) |
| Same-period ship | `SAME_PERIOD_SHIP` (fresh dispatch assumption) |
| Recovery capacity | `RECOVERY_FRAC` (+ scenario multipliers) |
| Economics of effort | Stepped recovery cost tiers |
| Cold inventory capital | Holding views (incremental proxy vs total FG) |
| Quality / dairy realism | Recovery ≠ rework of spoiled milk (documented) |

Not yet hard constraints in code: lab release hours, explicit shelf-life scrap, labor headcount.

---

## 7. Objective function

**Primary (modeled)**

```text
Maximize Net Operational Opportunity
  ≈ Protected CM − Recovery cost − Incremental holding proxy
```

**Headline reporting metric (already in engine)**

```text
Net CM Opportunity = Protected CM − Recovery cost
```

**Context metrics (not primary objective)**

- Residual CM exposure (still at risk after mitigation path)  
- Net CM after **total FG** holding (working-capital stress lens)  

**Soft service goal (narrative)**

- Prefer protecting high-CM / high-priority fresh SKUs when ranking opportunities  

---

## 8. Required outputs (decision product)

For portfolio / dashboard consumers:

1. Ranked SKU–Period opportunities by **Net CM Opportunity** (not by worst OEE)  
2. Unit gap waterfall (inventory / recovery / substitution / residual)  
3. $ bridge: Protected CM → recovery cost → net opportunity  
4. Holding **range**: none / incremental proxy / total FG  
5. Sensitivity: recovery fraction, same-period ship  
6. Clear labels: **Modeled · assumption-driven · not a forecast**  

---

## 9. Success criteria (for this portfolio)

| Criterion | Pass if |
|-----------|---------|
| Decision clarity | Owner, actions, objective are explicit |
| Economic honesty | Exposure ≠ opportunity; holding views separated |
| Traceability | Units reconcile; integrity checks pass |
| Dairy fit | CIP/cold store/filler language; no spoiled-milk rework claim |
| Non-claim | No presentation as real-plant benefit |

---

## 10. Baseline vs action (conceptual counterfactual)

| World | Definition |
|-------|------------|
| **Baseline (A0)** | No extra recovery/divert beyond ordinary plan; gap only absorbed by policy inventory rules |
| **Action path** | Inventory absorb + recovery + alternate line as in the engine waterfall |

**Decision-relevant value** ≈ economics of the action path versus accepting a larger residual shortfall.  
Implemented in **`07_baseline_vs_action.py`**: baseline = inventory-only; action = full waterfall; risk-adjusted = Δ Net × `P_REALIZE` (see `final/Decision_Action_Summary.json`).

---

## 11. Critical assumptions to stress

| Assumption | Default | Why it moves the decision |
|------------|---------|---------------------------|
| `RECOVERY_FRAC` | 0.20 | Scales recoverable units |
| `SAME_PERIOD_SHIP` | 1 | Fresh product often cannot wait |
| Stepped recovery costs | $2 / $7 / $14 | Marginal OT/co-pack cost |
| Holding WACC proxy | 18% | Working-capital lens |
| Single global recovery rate | — | Real dairy: by stop reason / SKU |

---

## 12. One-sentence brief

> **Weekly, the planning manager at North Valley Dairy chooses whether to buffer, recover, divert, or accept shortfall on each SKU so modeled net CM after incremental effort is improved—under filler capability, cold inventory, and explicit recovery-cost assumptions—without treating results as a real-plant forecast.**


---

## Official ranking objective (v1.9.0)

| Use | Metric |
|-----|--------|
| **Primary ranking (decision page default)** | `Expected_RiskAdjustedCM` = max(0, NetCMOpportunity) × P_REALIZE |
| **Capacity-aware ranking** | `NetCM_per_ConstrainedHour` |
| **Headline mitigation value** | `NetCMOpportunity` = ProtectedCM − RecoveryCost |
| **Context only (not ranking)** | Net CM after total FG holding; residual CM exposure |

**A1 buffer clarification:** Ordinary opening-inventory absorption is part of **both** baseline and action (policy inventory use). It is **not** a separate incremental campaign. Incremental actions are **A2 recovery** and **A3 alternate-line divert**. "Accept shortfall" is the residual after those paths.
