"""
OEE → Revenue → CM — Portfolio Dashboard (Streamlit)
Reads outputs from final/ and output/; does not re-run the pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
FIN = ROOT / "final"
OUT = ROOT / "output"

st.set_page_config(
    page_title="Operations → Financial Impact Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_json(name: str) -> dict:
    p = FIN / name
    if not p.exists():
        return {}
    return json.loads(p.read_text())


@st.cache_data
def load_csv(folder: str, name: str) -> pd.DataFrame:
    p = (FIN if folder == "final" else OUT) / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def fmt_money(x, digits=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    if abs(x) >= 1e6:
        return f"${x/1e6:.{digits}f} M"
    if abs(x) >= 1e3:
        return f"${x/1e3:.{digits}f} K"
    return f"${x:,.{digits}f}"


def fmt_num(x, digits=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return f"{x:,.{digits}f}"


def sidebar_meta(summary: dict, assumptions: pd.DataFrame):
    st.sidebar.title("Financial Impact → CM")
    st.sidebar.caption("North Valley Dairy (synthetic) · not a real plant")
    st.sidebar.markdown("---")
    mode = summary.get("recovery_cost_mode") or summary.get("context", {}).get("recovery_cost_mode")
    # fallback from assumptions
    if assumptions is not None and len(assumptions):
        m = dict(zip(assumptions.Parameter.astype(str), assumptions.Value.astype(str)))
        st.sidebar.markdown("**Resolved assumptions**")
        st.sidebar.text(f"RECOVERY_FRAC = {m.get('RECOVERY_FRAC', '—')}")
        st.sidebar.text(f"COST_MODE = {m.get('RECOVERY_COST_MODE', mode or '—')}")
        st.sidebar.text(f"WACC = {m.get('HOLDING_COST_ANNUAL_WACC', '—')}")
        st.sidebar.text(f"SAME_PERIOD_SHIP = {m.get('SAME_PERIOD_SHIP', '—')}")
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Page",
        ["Executive", "Decision", "P&L Bridge", "Product deep dive", "Sensitivity", "Scenarios"],
        index=0,
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("**MODEL STATUS**")
    st.sidebar.text("Domain: Imaginary dairy")
    st.sidebar.text("Data: Synthetic")
    st.sidebar.text("Period: FY2024")
    st.sidebar.text("Scenario: Baseline")
    st.sidebar.text("Forecast?: No")
    integ = load_json("integrity_checks.json")
    n = len(integ.get("checks") or [])
    st.sidebar.text(f"Integrity: {'PASS' if integ.get('passed') else 'FAIL'} ({n} checks)")
    st.sidebar.caption("Reads final/ + output/ only · pipeline not re-run in-app")
    return page




def page_pl_bridge():
    st.header("P&L Bridge — Budget to Actual Gross Profit")
    st.caption("Modeled · no fixed overhead · product-level MixEffect = 0")
    summary = load_json("PL_Bridge_Summary.json")
    if summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Budget Revenue", f"${summary.get('total_budget_revenue', 0):,.0f}")
        c2.metric("Actual Revenue", f"${summary.get('total_actual_revenue', 0):,.0f}")
        c3.metric("Budget GP", f"${summary.get('total_budget_gp', 0):,.0f}")
        c4.metric("Actual GP", f"${summary.get('total_actual_gp', 0):,.0f}",
                  delta=f"{summary.get('gp_variance', 0):+,.0f}")
        st.caption(
            f"Yield variance ${summary.get('total_yield_variance', 0):,.0f} · "
            f"bridge max |err| rev={summary.get('revenue_bridge_max_abs_error', 0):.2e} "
            f"cogs={summary.get('cogs_bridge_max_abs_error', 0):.2e}"
        )
    path = FIN / "PL_Bridge_Summary.csv"
    if path.exists():
        df = pd.read_csv(path)
        st.subheader("By period")
        st.dataframe(df, use_container_width=True, hide_index=True)
        if len(df):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.PeriodKey.astype(str), y=df.BudgetGP, name="Budget GP", line=dict(dash="dash")))
            fig.add_trace(go.Scatter(x=df.PeriodKey.astype(str), y=df.ActualGP, name="Actual GP"))
            fig.update_layout(height=360, margin=dict(t=40, b=40), title="Gross Profit trend")
            st.plotly_chart(fig, use_container_width=True)
            # simple waterfall for totals
            tot_b = float(df.BudgetRevenue.sum())
            tot_v = float(df.VolumeEffect.sum())
            tot_p = float(df.PriceEffect.sum())
            tot_a = float(df.ActualRevenue.sum())
            fig2 = go.Figure(go.Waterfall(
                x=["Budget Rev", "Volume", "Price", "Actual Rev"],
                y=[tot_b, tot_v, tot_p, tot_a],
                measure=["absolute", "relative", "relative", "total"],
            ))
            fig2.update_layout(height=360, title="Revenue bridge (portfolio total)", margin=dict(t=40, b=40))
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Run 10_pl_bridge.py (or run_pipeline.py) to generate PL_Bridge_Summary.csv")
    det = FIN / "PL_Bridge_Detail.csv"
    if det.exists():
        with st.expander("Product × period detail"):
            st.dataframe(pd.read_csv(det).head(50), use_container_width=True, hide_index=True)


def page_decision(summary: dict):
    st.header("Decision — Baseline vs Action")
    st.info(
        "**Baseline** = inventory buffer only. **Action** = recovery + alternate line. "
        "Risk-adjusted uses assumed **P_REALIZE** (not statistically fitted)."
    )
    dec = load_json("Decision_Action_Summary.json")
    port = (dec or {}).get("portfolio") or {}
    p_real = (dec or {}).get("p_realize", "—")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Baseline CM exposure", fmt_money(port.get("baseline_cm_exposure")))
    c2.metric("Action CM exposure", fmt_money(port.get("action_cm_exposure")))
    c3.metric("Net operational CM", fmt_money(port.get("delta_net_operational_cm")))
    c4.metric(f"Risk-adjusted (P={p_real})", fmt_money(port.get("expected_risk_adjusted_cm")))
    st.caption(
        f"Exposure avoided: {fmt_money(port.get('delta_cm_exposure_avoided'))} · "
        f"Positive Δ periods: {port.get('rows_with_positive_delta_net')} / {port.get('rows')}"
    )
    path = FIN / "Decision_Action_Comparison.csv"
    if path.exists():
        df = pd.read_csv(path)
        st.subheader("Rank by $ value (expected risk-adjusted CM)")
        top = df.sort_values("Expected_RiskAdjustedCM", ascending=False).head(15)
        show = top[[
            "PeriodKey", "ProductID", "RecommendedAction",
            "Delta_NetOperationalCM", "Expected_RiskAdjustedCM",
            "MitigationHours", "NetCM_per_ConstrainedHour",
        ]]
        st.dataframe(show, use_container_width=True, hide_index=True)
        fig = px.bar(
            top.head(10),
            x="ProductID",
            y="Expected_RiskAdjustedCM",
            color="RecommendedAction",
            title="Top 10 by expected risk-adjusted CM",
        )
        fig.update_layout(height=340, margin=dict(t=40, b=40))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Rank by capacity efficiency (Net CM per constrained hour)")
        st.caption(
            "Mitigation hours ≈ recovered/primary rate + substituted/alt rate. "
            "High total $ and high $/hour rankings can differ — use both."
        )
        cap = df[df["MitigationHours"].fillna(0) > 0].sort_values(
            "NetCM_per_ConstrainedHour", ascending=False
        ).head(15)
        if len(cap):
            st.dataframe(
                cap[[
                    "PeriodKey", "ProductID", "MitigationHours",
                    "NetCM_per_ConstrainedHour", "ProtectedCM_per_ConstrainedHour",
                    "Delta_NetOperationalCM",
                ]],
                use_container_width=True, hide_index=True,
            )
            fig2 = px.bar(
                cap.head(10),
                x="ProductID",
                y="NetCM_per_ConstrainedHour",
                title="Top 10 by Net CM / constrained hour",
            )
            fig2.update_layout(height=340, margin=dict(t=40, b=40))
            st.plotly_chart(fig2, use_container_width=True)

        sens_p = FIN / "Sensitivity_P_Realize.csv"
        if sens_p.exists():
            st.subheader("P_REALIZE sensitivity")
            st.caption("Assumption-based realization factor — not empirically fitted.")
            sp = pd.read_csv(sens_p)
            st.dataframe(sp, use_container_width=True, hide_index=True)
            fig3 = px.line(sp, x="P_REALIZE", y="Expected_RiskAdjustedCM", markers=True,
                           title="Expected risk-adjusted CM vs P_REALIZE")
            fig3.update_layout(height=320, margin=dict(t=40, b=40))
            st.plotly_chart(fig3, use_container_width=True)

        pareto_path = FIN / "Downtime_Reason_Pareto.csv"
        if pareto_path.exists():
            st.subheader("Downtime reason Pareto (minutes)")
            st.caption("Descriptive only — recovery is not yet reason-specific.")
            pr = pd.read_csv(pareto_path)
            st.dataframe(pr.head(10), use_container_width=True, hide_index=True)
    else:
        st.warning("Run 07_baseline_vs_action.py to generate Decision_Action_Comparison.csv")


def page_executive(summary: dict, impact: pd.DataFrame, sens: pd.DataFrame):
    st.header("Executive decision overview — North Valley Dairy")
    st.info(
        "**Modeled / assumption-driven / not a forecast.** Synthetic data. "
        "Headline opportunity is **Net CM opportunity**; total-FG holding is context only."
    )

    oee = summary.get("oee_avg_time_weighted") or summary.get("oee_baseline_time_weighted")
    if oee is None:
        oee = (summary.get("context") or {}).get("oee_baseline_time_weighted")
    gap = summary.get("gap_waterfall") or {}

    st.subheader("Financial headline")
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Net CM opportunity", fmt_money(summary.get("net_cm_opportunity")))
    h2.metric("Gross gap (EA)", fmt_num(gap.get("gross_gap") or summary.get("total_gross_gap_units")))
    h3.metric("CM exposure (residual lost)", fmt_money(summary.get("cm_exposure")))
    h4.metric("Time-weighted OEE", f"{float(oee):.1%}" if oee is not None else "—")
    dec = load_json("Decision_Action_Summary.json")
    if dec and (dec.get("portfolio") or {}).get("expected_risk_adjusted_cm") is not None:
        st.caption(
            f"Risk-adjusted (× P_REALIZE={(dec or {}).get('p_realize')}): "
            f"**{fmt_money((dec.get('portfolio') or {}).get('expected_risk_adjusted_cm'))}** "
            f"— see Decision page"
        )

    st.subheader("Holding-cost views (do not conflate)")
    k1, k2, k3 = st.columns(3)
    k1.metric(
        "After incremental holding",
        fmt_money(summary.get("net_cm_after_incremental_holding")),
        delta=f"incr. cost {fmt_money(summary.get('incremental_holding_cost'))}",
    )
    k2.metric(
        "After total FG holding",
        fmt_money(summary.get("net_cm_after_holding")),
        delta=f"total hold {fmt_money(summary.get('inventory_holding_cost'))}",
    )
    k3.metric("Protected CM − recovery cost", fmt_money(summary.get("protected_cm")))
    st.caption(
        "Incremental holding ≈ cost on inventory **absorbed into the gap**. "
        "Total FG holding is **not** proven OEE-attributable — sensitivity/context only."
    )

    c5, c6 = st.columns(2)
    c5.metric("Protected CM", fmt_money(summary.get("protected_cm")))
    c6.metric("Recovery cost (stepped)", fmt_money(summary.get("recovery_cost")))

    st.subheader("Operational gap → financial exposure")
    if gap:
        labels = ["Gross gap", "Inventory absorbed", "Recovered", "Substituted", "Lost sales"]
        # waterfall style: start gross, then negative components
        measures = ["absolute", "relative", "relative", "relative", "total"]
        inv = -float(gap.get("inventory_absorbed") or 0)
        rec = -float(gap.get("recovered") or 0)
        sub = -float(gap.get("substituted") or 0)
        lost = float(gap.get("lost_sales") or 0)
        gross = float(gap.get("gross_gap") or 0)
        fig = go.Figure(go.Waterfall(
            name="Units",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Gross gap", "− Inventory", "− Recovered", "− Substituted", "Lost sales"],
            y=[gross, inv, rec, sub, lost],
            connector={"line": {"color": "#888"}},
            decreasing={"marker": {"color": "#0d9488"}},
            increasing={"marker": {"color": "#2563eb"}},
            totals={"marker": {"color": "#dc2626"}},
        ))
        fig.update_layout(height=380, margin=dict(t=30, b=40, l=40, r=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Identity: GrossGap = InvAbs + Recovered + Substituted + LostSales")

    st.subheader("Contribution-margin decision bridge")
    prot = float(summary.get("protected_cm") or (summary.get("opportunity_bridge") or {}).get("protected_cm_from_recovery_and_substitution") or 0)
    rcost = float(summary.get("recovery_cost") or 0)
    hold = float(summary.get("inventory_holding_cost") or 0)
    net = float(summary.get("net_cm_opportunity") or 0)
    net_h = float(summary.get("net_cm_after_holding") or (net - hold))
    fig2 = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total", "relative", "total"],
        x=["Protected CM", "− Recovery cost", "Net CM opportunity", "− Holding cost", "Net after holding"],
        y=[prot, -rcost, net, -hold, net_h],
        decreasing={"marker": {"color": "#ea580c"}},
        increasing={"marker": {"color": "#2563eb"}},
        totals={"marker": {"color": "#7c3aed"}},
        connector={"line": {"color": "#888"}},
    ))
    fig2.update_layout(height=380, margin=dict(t=30, b=40, l=40, r=20))
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Identity: NetCMOpportunity = ProtectedCM − RecoveryCost. Total-FG holding is a separate context metric.")

    if len(sens):
        st.subheader("Recovery fraction sensitivity (precomputed)")
        fig3 = px.bar(
            sens,
            x="RecoveryFrac",
            y="NetCMOpportunity",
            text=sens["NetCMOpportunity"].map(lambda v: fmt_money(v, 2)),
            labels={"RecoveryFrac": "Recovery fraction", "NetCMOpportunity": "Net CM opportunity ($)"},
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(height=360, margin=dict(t=30, b=40))
        st.plotly_chart(fig3, use_container_width=True)


def page_product(impact: pd.DataFrame, products: list):
    st.header("Product deep dive")
    if impact.empty:
        st.warning("FactImpact_ProductPeriod.csv not found.")
        return

    left, right = st.columns([1, 3])
    with left:
        prod = st.selectbox("Product", options=["(All)"] + products)
        periods = sorted(impact.PeriodKey.astype(str).unique())
        per = st.multiselect("Periods", periods, default=periods)
    df = impact.copy()
    df["PeriodKey"] = df.PeriodKey.astype(str)
    if per:
        df = df[df.PeriodKey.isin(per)]
    if prod != "(All)":
        df = df[df.ProductID == prod]

    st.subheader("Totals for selection")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross gap", fmt_num(df.GrossGap.sum()))
    m2.metric("Lost sales units", fmt_num(df.PotentialLostSalesUnits.sum()))
    m3.metric("CM exposure", fmt_money(df.CMExposure.sum()))
    m4.metric(
        "Net CM opportunity",
        fmt_money(df.NetCMOpportunity.sum()),
    )
    if "HoldingCost" in df.columns:
        m5, m6 = st.columns(2)
        m5.metric("Holding cost", fmt_money(df.HoldingCost.sum()))
        if "NetCM_after_Holding" in df.columns:
            m6.metric("Net CM after holding", fmt_money(df.NetCM_after_Holding.sum()))

    # Product ranking
    agg_map = dict(
        GrossGap=("GrossGap", "sum"),
        LostSales=("PotentialLostSalesUnits", "sum"),
        CMExposure=("CMExposure", "sum"),
        NetCMOpportunity=("NetCMOpportunity", "sum"),
    )
    if "HoldingCost" in df.columns:
        agg_map["HoldingCost"] = ("HoldingCost", "sum")
    agg = (
        df.groupby("ProductID", as_index=False)
        .agg(**agg_map)
        .sort_values("NetCMOpportunity", ascending=False)
    )

    fig = px.bar(
        agg,
        x="ProductID",
        y="NetCMOpportunity",
        color="CMExposure",
        labels={"NetCMOpportunity": "Net CM opportunity ($)"},
        title="Product ranking by Net CM opportunity (not OEE)",
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Detail table")
    show_cols = [
        c
        for c in [
            "PeriodKey",
            "ProductID",
            "LineID",
            "OEE",
            "GrossGap",
            "InventoryAbsorbed",
            "RecoveredUnits",
            "SubstitutedUnits",
            "PotentialLostSalesUnits",
            "CMExposure",
            "ProtectedCM",
            "RecoveryCost",
            "NetCMOpportunity",
            "HoldingCost",
            "NetCM_after_Holding",
        ]
        if c in df.columns
    ]
    st.dataframe(
        df[show_cols].sort_values(["NetCMOpportunity"], ascending=False),
        use_container_width=True,
        height=420,
    )


def page_sensitivity(sens: pd.DataFrame, ship: pd.DataFrame, impact: pd.DataFrame, assumptions: pd.DataFrame):
    st.header("Sensitivity")
    st.caption("Recovery-frac curves are precomputed by the pipeline. Holding cost can be re-scaled locally by WACC.")

    tab1, tab2, tab3 = st.tabs(["Recovery fraction", "Same-period ship", "Holding WACC (local)"])

    with tab1:
        if sens.empty:
            st.warning("Sensitivity_RecoveryFrac.csv missing — run 03_sensitivity_recovery.py")
        else:
            st.dataframe(sens, use_container_width=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sens.RecoveryFrac, y=sens.ProtectedCM, name="Protected CM", mode="lines+markers"
            ))
            fig.add_trace(go.Scatter(
                x=sens.RecoveryFrac, y=sens.RecoveryCost, name="Recovery cost", mode="lines+markers"
            ))
            fig.add_trace(go.Scatter(
                x=sens.RecoveryFrac, y=sens.NetCMOpportunity, name="Net CM opportunity", mode="lines+markers"
            ))
            fig.update_layout(
                xaxis_title="Recovery fraction",
                yaxis_title="$",
                height=400,
                legend=dict(orientation="h"),
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if ship.empty:
            st.warning("Sensitivity_SamePeriodShip.csv missing — run 06_sensitivity_same_period_ship.py")
        else:
            st.dataframe(ship, use_container_width=True)
            fig = px.bar(
                ship,
                x="Label",
                y="TotalLostVsDemand",
                text="TotalLostVsDemand",
                title="Lost units vs firm demand (roll-forward sensitivity)",
            )
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if impact.empty or "AvgInventory" not in impact.columns:
            st.warning("Impact needs AvgInventory / HoldingCost from engine v1.7+")
        else:
            m = {}
            if len(assumptions):
                m = dict(zip(assumptions.Parameter.astype(str), assumptions.Value))
            base_wacc = float(m.get("HOLDING_COST_ANNUAL_WACC", 0.18))
            wacc = st.slider("Annual holding WACC", 0.05, 0.35, float(base_wacc), 0.01)
            # Recompute holding from avg inv * VC implicit in HoldingCost at base WACC
            # HoldingCost_base = AvgInv * VC * (base_wacc/12) => HoldingCost_new = base * (wacc/base_wacc)
            scale = wacc / base_wacc if base_wacc else 1.0
            hold = float(impact.HoldingCost.sum()) * scale
            net = float(impact.NetCMOpportunity.sum())
            st.metric("Baseline Net CM opportunity", fmt_money(net))
            st.metric(f"Holding cost @ {wacc:.0%} WACC", fmt_money(hold))
            st.metric("Net CM after holding", fmt_money(net - hold))
            st.caption(
                "Local rescale assumes holding is linear in WACC; does not re-run the full pipeline."
            )


def page_scenarios(scen: pd.DataFrame):
    st.header("Scenario results")
    if scen.empty:
        st.warning("Scenario_Results.csv missing")
        return
    st.caption(
        "Column **NetCMImpact_after_RecoveryCost** is scenario-specific "
        "(Δ CM exposure − scenario recovery cost), not the baseline NetCMOpportunity identity."
    )
    st.dataframe(scen, use_container_width=True)

    ycol = "NetCMImpact_after_RecoveryCost" if "NetCMImpact_after_RecoveryCost" in scen.columns else "CMImpact"
    fig = px.bar(
        scen,
        x="ScenarioID",
        y=ycol,
        color="ScenarioType",
        hover_data=[c for c in ["ScenarioName", "LostUnits_scenario", "CMExposure_scenario"] if c in scen.columns],
        title=ycol,
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    if "LostUnits_baseline" in scen.columns and "LostUnits_scenario" in scen.columns:
        melt = scen.melt(
            id_vars=["ScenarioID"],
            value_vars=["LostUnits_baseline", "LostUnits_scenario"],
            var_name="Series",
            value_name="LostUnits",
        )
        fig2 = px.bar(
            melt,
            x="ScenarioID",
            y="LostUnits",
            color="Series",
            barmode="group",
            title="Lost units: baseline vs scenario",
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)


def main():
    summary = load_json("Executive_Summary_Numbers.json")
    impact = load_csv("final", "FactImpact_ProductPeriod.csv")
    sens = load_csv("final", "Sensitivity_RecoveryFrac.csv")
    ship = load_csv("final", "Sensitivity_SamePeriodShip.csv")
    scen = load_csv("final", "Scenario_Results.csv")
    assumptions = load_csv("output", "ModelAssumptions.csv")

    page = sidebar_meta(summary, assumptions)

    if page == "Executive":
        page_executive(summary, impact, sens)
    elif page == "P&L Bridge":
        page_pl_bridge()
    elif page == "Decision":
        page_decision(summary)
    elif page == "Product deep dive":
        products = sorted(impact.ProductID.astype(str).unique()) if len(impact) else []
        page_product(impact, products)
    elif page == "Sensitivity":
        page_sensitivity(sens, ship, impact, assumptions)
    else:
        page_scenarios(scen)


if __name__ == "__main__":
    main()
