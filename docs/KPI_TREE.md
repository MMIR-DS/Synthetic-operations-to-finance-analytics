# KPI Tree — North Valley Dairy (synthetic)

**Version:** 1.9.0.1  
**Use:** Connect decision objective to operational drivers and model fields  

---

## 1. Decision-level outcome

```text
Realized CM benefit (modeled target)
└── Net operational opportunity
    ├── Protected CM                          (+)
    │   └── (Recovered + Substituted units) × CM/unit
    ├── Recovery / mitigation cost            (−)
    │   └── Stepped or flat $/unit on mitigated volume
    └── Incremental holding proxy (optional)  (−)
        └── Absorbed units × unit holding rate
```

**Portfolio headline (engine identity)**

```text
Net CM Opportunity = Protected CM − RecoveryCost
```

**Do not equate with**

- Residual CM exposure (margin still on *unmet* units)  
- Total FG holding cost (context / stress only)  
- EBITDA, cash, or guaranteed plant benefit  

---

## 2. Volume tree (how units appear)

```text
Additional / protected shipped units (modeled)
├── Inventory absorption (opening available FG)
├── Recovered units (OT / extra run on primary path)
└── Substituted units (alternate capable line)
```

```text
Residual lost sales units (modeled)
└── Gross gap − inventory absorbed − recovered − substituted
```

```text
Gross gap
└── Firm demand − primary shippable supply
    (primary supply depends on SAME_PERIOD_SHIP rule)
```

---

## 3. Operational driver tree

```text
Primary good supply
├── Scheduled / run time
├── Availability (uptime vs CIP, failure, changeover, shortage)
├── Performance (rate vs standard)
├── Quality (good vs scrap)
├── Standard rate on primary line
└── Line–SKU capability
```

```text
Mitigation capacity
├── RECOVERY_FRAC (assumption)
├── Remaining gap after inventory
├── Alternate line slack hours
└── Capability bridge (SKU on alt line)
```

---

## 4. Financial context tree

```text
Commercial margin context
├── Actual net revenue & CM (synthetic P&L-like totals)
├── Budget / plan CM (for PVM)
└── PVM effects (volume, mix, price, residual)
    └── Ops-relevant: volume/availability-type gaps
        Market-type: price & mix (not fixed by filler OT)
```

---

## 5. KPI dictionary (decision-critical)

| KPI | Definition (portfolio) | Grain | Unit | Model field / source | Limit of interpretation |
|-----|------------------------|-------|------|----------------------|-------------------------|
| OEE | A × P × Q | Run / aggregate | ratio | FactOEE_Run | Not a $ figure |
| Gross gap | Demand − primary supply | Product×Period | EA | GrossGap | Before mitigation |
| Inventory absorbed | Gap closed from opening FG | Product×Period | EA | InventoryAbsorbed | Buffer, not free |
| Recovered units | Gap closed via recovery frac | Product×Period | EA | RecoveredUnits | Assumes recovery possible |
| Substituted units | Gap closed on alt line | Product×Period | EA | SubstitutedUnits | Slack + capability |
| Lost sales units | Residual gap | Product×Period | EA | PotentialLostSalesUnits | Modeled exposure |
| CM exposure | Lost units × CM/unit | Product×Period | $ | CMExposure | Still at risk |
| Protected CM | Mitigated units × CM/unit | Product×Period | $ | ProtectedCM | Gross mitigation value |
| Recovery cost | Stepped/flat cost on mitigated | Product×Period | $ | RecoveryCost | Effort cost |
| Net CM opportunity | Protected − recovery cost | Product×Period | $ | NetCMOpportunity | Headline modeled value |
| Incremental holding proxy | Absorbed × hold rate | Product×Period | $ | IncrementalHoldingCost | Not full counterfactual |
| Total FG holding | Avg FG × VC × WACC/12 | Product×Period | $ | HoldingCost | Context only |

**Owner (narrative):** Planning owns action choice; Finance owns CM definitions; Ops owns loss tree.

---

## 6. Ranking rule (business analytics)

```text
Priority score (portfolio default)
= Net CM Opportunity
```

Not default:

```text
Priority ≠ lowest OEE
Priority ≠ largest unit gap alone
```

Optional future:

```text
Risk-adjusted = Net CM Opportunity × P(realize)
```

---

## 7. Sensitivity KPIs

| Lever | KPI movement |
|-------|----------------|
| Recovery fraction ↑ | Recovered units ↑, recovery cost ↑, net CM usually ↑ but marginal cost tiers matter |
| Same-period ship off | Gross gap ↑ sharply (fresh dispatch lag) |
| WACC ↑ | Total/incremental holding $ ↑ |

---

## 8. One-line tree

> **Decision KPI = modeled net CM from mitigation; volume KPI = gap waterfall; ops KPI = OEE loss tree; finance guardrail = exposure vs opportunity vs holding range.**
