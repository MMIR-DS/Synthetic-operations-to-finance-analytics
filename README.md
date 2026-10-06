# OEE → Revenue → Contribution Margin Pipeline

**Version 1.9.0.1** — imaginary dairy factory · [Persian README](README.fa.md) · `streamlit run dashboard/app_fa.py`

**Synthetic operations-to-finance analytics portfolio project**

Translates manufacturing OEE losses into **unit gaps**, **shipment shortfalls**, **revenue exposure**, and **contribution-margin impact** — with inventory roll-forward, recovery/substitution, PVM reconciliation, scenario analysis, and integrity checks.

> **Data is synthetic.** Figures are model outputs under documented assumptions — **not** a real-plant forecast.

> **Authoritative numbers:** [`final/Executive_Summary_Numbers.json`](final/Executive_Summary_Numbers.json) after any run.

> **So what:** Modeled Net CM opportunity ~**$1.28M**. After incremental holding ~**$1.26M**. After total FG holding ~**$0.43M** (context only). See `final/EXECUTIVE_CASE_STUDY.md`.

## Domain

North Valley Dairy (synthetic): milk, yogurt, cheese/butter · cold store · CIP/changeover/filler downtime · retail packs (EA).

## How to run

```bash
pip install -r requirements.txt
python run_pipeline.py
streamlit run dashboard/app.py
# Persian:
streamlit run dashboard/app_fa.py
```

Pipeline order: `01→02→03→06→07→08→09→10→tests→05→04`

## Key design points

- OEE is **not** multiplied by revenue; path is gap → inventory → recovery → substitution → lost sales → CM
- `NetCMOpportunity = ProtectedCM − RecoveryCost`
- Transaction facts (production, downtime, sales) + periodic inventory snapshot + derived `FactOEE_Run` / `FactImpact_ProductPeriod`
- Stepped recovery costs; holding cost at 18% WACC proxy
- 24 integrity checks on the reference run

## Layout

```text
run_pipeline.py          # orchestrator
01_…10_*.py              # generate → engine → sensitivity → decision → P&L
shared/cost_model.py     # stepped recovery cost
tests/                   # identity tests
docs/                    # decision brief, causal map, KPI tree
dashboard/               # Streamlit EN/FA
final/                   # outputs, integrity, case study
```

## License / framing

Portfolio demonstration. Synthetic data. Not investment advice or plant claims.
