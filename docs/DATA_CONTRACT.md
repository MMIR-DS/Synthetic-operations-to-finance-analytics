# Data Contract

Portfolio release: **1.9.0.1** · Decision-model baseline: **1.9.0**

**Document type:** Data requirements for the decision in DECISION_BRIEF.md

## 1. Entities and grains

| Entity | Grain | Business key | Decision use |
|--------|-------|--------------|--------------|
| Product (SKU) | product | ProductID | What to prioritize |
| Line | line | LineID | Capacity / alternate |
| Period | month | PeriodKey | Planning bucket |
| Date | day | DateKey | Run/downtime/sales events |
| Location | warehouse | LocationID | Inventory snapshot |
| Scenario | scenario | ScenarioID | Plan / stress |

## 2. Fact groups mapped to questions

| Fact group | Answers |
|------------|---------|
| Production + OEE_Run | How much good output vs plan time? |
| Downtime | Which reasons consume time? |
| Demand + FinancialPlan | What was asked for / budgeted? |
| InventorySnapshot | What buffer exists this period? |
| Impact_ProductPeriod | Gap, mitigation, CM opportunity |
| Sales | What shipped (reconciles to shipments)? |

## 3. Future data needs (not in synthetic scope)

- Empirical recovery rates by downtime class
- True multi-period backlog / lead times
- Customer-level allocation priorities
- Measured P_REALIZE from closed-loop actions

## 4. Quality rules

- No duplicate keys at declared grain
- GrossGap = InvAbs + Recovered + Substituted + LostSales
- NetCMOpportunity = ProtectedCM - RecoveryCost
- Variable cost ≤ price at product level
