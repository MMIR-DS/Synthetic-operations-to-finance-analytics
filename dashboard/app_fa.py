"""
داشبورد فارسی OEE → حاشیه مشارکت (RTL + برچسب شمسی)
دادهها از final/ و output/ — پایپلاین را دوباره اجرا نمیکند.
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

# --- تبدیل ساده میلادی → شمسی (بدون وابستگی خارجی) ---
_J_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def _gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + (days % 31)
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def period_label_fa(period_key) -> str:
    """202401 → دی ۱۴۰۲ (تقریبی بر اساس روز میانی ماه میلادی)."""
    s = str(period_key)
    if len(s) < 6:
        return s
    y, m = int(s[:4]), int(s[4:6])
    jy, jm, _ = _gregorian_to_jalali(y, m, 15)
    return f"{_J_MONTHS[jm - 1]} {jy}"


def period_label_dual(period_key) -> str:
    s = str(period_key)
    return f"{period_label_fa(s)} ({s[:4]}/{s[4:6]})"


st.set_page_config(
    page_title="OEE تا حاشیه مشارکت",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  html, body, [class*="css"]  { font-family: Tahoma, "Vazirmatn", "Segoe UI", sans-serif; }
  .stApp { direction: rtl; text-align: right; }
  [data-testid="stSidebar"] { direction: rtl; text-align: right; }
  [data-testid="stMetricValue"] { direction: ltr; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_json(name: str) -> dict:
    p = FIN / name
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data
def load_csv(folder: str, name: str) -> pd.DataFrame:
    p = (FIN if folder == "final" else OUT) / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


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
        return f"{float(x):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def main():
    summary = load_json("Executive_Summary_Numbers.json")
    impact = load_csv("final", "FactImpact_ProductPeriod.csv")
    sens = load_csv("final", "Sensitivity_RecoveryFrac.csv")
    ship = load_csv("final", "Sensitivity_SamePeriodShip.csv")
    scen = load_csv("final", "Scenario_Results.csv")
    assumptions = load_csv("output", "ModelAssumptions.csv")

    st.sidebar.title("OEE → حاشیه مشارکت")
    st.sidebar.caption("لبنیات دره شمالی (فرضی) — نه کارخانه واقعی")
    st.sidebar.markdown("---")
    if len(assumptions):
        m = dict(zip(assumptions.Parameter.astype(str), assumptions.Value.astype(str)))
        st.sidebar.markdown("**فرضهای مدل**")
        st.sidebar.text(f"نرخ بازیابی = {m.get('RECOVERY_FRAC', '—')}")
        st.sidebar.text(f"حالت هزینه = {m.get('RECOVERY_COST_MODE', '—')}")
        st.sidebar.text(f"WACC نگهداری = {m.get('HOLDING_COST_ANNUAL_WACC', '—')}")
        st.sidebar.text(f"ارسال هماندوره = {m.get('SAME_PERIOD_SHIP', '—')}")
    page = st.sidebar.radio(
        "صفحه",
        ["خلاصه مدیریتی", "تصمیم", "تحلیل محصول", "حساسیت", "سناریوها"],
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("**وضعیت مدل**")
    st.sidebar.text("حوزه: لبنیات فرضی")
    st.sidebar.text("داده: مصنوعی")
    st.sidebar.text("دوره: FY2024")
    st.sidebar.text("پیش‌بینی؟ خیر")
    integ = load_json("integrity_checks.json")
    st.sidebar.text(f"یکپارچگی: {'PASS' if integ.get('passed') else 'FAIL'} ({len(integ.get('checks') or [])})")
    st.sidebar.caption("مبالغ به دلار مدل (USD) · کلیدهای زمانی در داده میلادیاند؛ برچسبها شمسی")

    if page == "تصمیم":
        page_decision(summary)
    elif page == "خلاصه مدیریتی":
        page_executive(summary, sens)
    elif page == "تحلیل محصول":
        products = sorted(impact.ProductID.astype(str).unique()) if len(impact) else []
        page_product(impact, products)
    elif page == "حساسیت":
        page_sensitivity(sens, ship, impact, assumptions)
    else:
        page_scenarios(scen)



def page_decision(summary: dict):
    st.header("تصمیم — پایه در برابر اقدام")
    st.info("پایه = فقط موجودی. اقدام = بازیابی + خط جایگزین. P_REALIZE فرض مدل است.")
    dec = load_json("Decision_Action_Summary.json")
    port = (dec or {}).get("portfolio") or {}
    a, b, c, d = st.columns(4)
    a.metric("در معرض پایه", fmt_money(port.get("baseline_cm_exposure")))
    b.metric("در معرض اقدام", fmt_money(port.get("action_cm_exposure")))
    c.metric("خالص عملیاتی", fmt_money(port.get("delta_net_operational_cm")))
    d.metric("تعدیل‌شده با ریسک", fmt_money(port.get("expected_risk_adjusted_cm")))
    path = FIN / "Decision_Action_Comparison.csv"
    if path.exists():
        df = pd.read_csv(path).sort_values("Expected_RiskAdjustedCM", ascending=False).head(15)
        st.dataframe(df[["PeriodKey", "ProductID", "RecommendedAction", "Delta_NetOperationalCM", "Expected_RiskAdjustedCM"]],
                     use_container_width=True, hide_index=True)

def page_executive(summary: dict, sens: pd.DataFrame):
    st.header("خلاصه مدیریتی — لبنیات دره شمالی")
    st.info(
        "همه ارقام **مدل‌شده / فرض‌محور / نه پیش‌بینی** هستند. "
        "هزینه بازیابی پلهای و هزینه نگهداری موجودی روی کل موجودی متوسط اعمال شده است."
    )
    st.success(
        "**پیام کلیدی:** فرصت خالص حاشیه مشارکت حدود **۱٫۱۲ میلیون دلار** پس از هزینه نگهداری "
        "به حدود **۰٫۲۸ میلیون دلار** میرسد — سیاست موجودی میتواند به اندازه بازیابی OEE مهم باشد."
    )

    oee = summary.get("oee_avg_time_weighted")
    if oee is None:
        oee = (summary.get("context") or {}).get("oee_baseline_time_weighted")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OEE وزنی زمانی", f"{float(oee):.1%}" if oee is not None else "—")
    c2.metric("در معرض حاشیه مشارکت", fmt_money(summary.get("cm_exposure")))
    c3.metric("★ فرصت خالص CM", fmt_money(summary.get("net_cm_opportunity")))
    c4.metric("پس از نگهداری افزایشی", fmt_money(summary.get("net_cm_after_incremental_holding")))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("حاشیه محافظتشده", fmt_money(summary.get("protected_cm")))
    c6.metric("هزینه بازیابی (پلهای)", fmt_money(summary.get("recovery_cost")))
    c7.metric("پس از نگهداری کل FG", fmt_money(summary.get("net_cm_after_holding")))
    gap = summary.get("gap_waterfall") or {}
    c8.metric("شکاف ناخالص (عدد)", fmt_num(gap.get("gross_gap") or summary.get("total_gross_gap_units")))

    st.subheader("تجزیه شکاف واحدی")
    if gap:
        labs = ["شکاف ناخالص", "جذب موجودی", "بازیابی", "جایگزینی خط", "فروش ازدسترفته"]
        vals = [
            float(gap.get("gross_gap") or 0),
            float(gap.get("inventory_absorbed") or 0),
            float(gap.get("recovered") or 0),
            float(gap.get("substituted") or 0),
            float(gap.get("lost_sales") or 0),
        ]
        fig = go.Figure(
            go.Bar(x=labs, y=vals, marker_color=["#2563eb", "#0d9488", "#14b8a6", "#2dd4bf", "#dc2626"])
        )
        fig.update_layout(height=380, margin=dict(t=20, b=40), yaxis_title="واحد")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("هویت: شکاف ناخالص = جذب موجودی + بازیابی + جایگزینی + فروش ازدسترفته")

    st.subheader("پل دلاری (بازیابی و نگهداری)")
    prot = float(summary.get("protected_cm") or 0)
    rcost = float(summary.get("recovery_cost") or 0)
    hold = float(summary.get("inventory_holding_cost") or 0)
    net = float(summary.get("net_cm_opportunity") or 0)
    neth = float(summary.get("net_cm_after_holding") or (net - hold))
    fig2 = go.Figure(
        go.Bar(
            x=["حاشیه محافظتشده", "هزینه بازیابی", "فرصت خالص CM", "هزینه نگهداری", "پس از نگهداری"],
            y=[prot, rcost, net, hold, neth],
            marker_color=["#2563eb", "#ea580c", "#7c3aed", "#f59e0b", "#16a34a"],
        )
    )
    fig2.update_layout(height=380, margin=dict(t=20, b=40), yaxis_title="دلار مدل")
    st.plotly_chart(fig2, use_container_width=True)

    if len(sens):
        st.subheader("حساسیت به نرخ بازیابی (از پیش محاسبهشده)")
        fig3 = px.line(
            sens,
            x="RecoveryFrac",
            y=["ProtectedCM", "RecoveryCost", "NetCMOpportunity"],
            markers=True,
            labels={"value": "دلار", "RecoveryFrac": "نرخ بازیابی", "variable": "سری"},
        )
        fig3.update_layout(height=360)
        st.plotly_chart(fig3, use_container_width=True)


def page_product(impact: pd.DataFrame, products: list):
    st.header("تحلیل محصول")
    if impact.empty:
        st.warning("فایل FactImpact در دسترس نیست.")
        return

    impact = impact.copy()
    impact["PeriodKey"] = impact.PeriodKey.astype(str)
    impact["PeriodFa"] = impact.PeriodKey.map(period_label_dual)

    left, right = st.columns([1, 3])
    with left:
        prod = st.selectbox("محصول", options=["(همه)"] + products)
        periods = sorted(impact.PeriodKey.unique())
        period_opts = {period_label_dual(p): p for p in periods}
        selected_labels = st.multiselect("دورهها (شمسی / میلادی)", list(period_opts.keys()), default=list(period_opts.keys()))
        per = [period_opts[x] for x in selected_labels]

    df = impact if not per else impact[impact.PeriodKey.isin(per)]
    if prod != "(همه)":
        df = df[df.ProductID == prod]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("شکاف ناخالص", fmt_num(df.GrossGap.sum()))
    m2.metric("فروش ازدسترفته", fmt_num(df.PotentialLostSalesUnits.sum()))
    m3.metric("در معرض CM", fmt_money(df.CMExposure.sum()))
    m4.metric("فرصت خالص CM", fmt_money(df.NetCMOpportunity.sum()))
    if "HoldingCost" in df.columns:
        a, b = st.columns(2)
        a.metric("هزینه نگهداری", fmt_money(df.HoldingCost.sum()))
        if "NetCM_after_Holding" in df.columns:
            b.metric("خالص پس از نگهداری", fmt_money(df.NetCM_after_Holding.sum()))

    agg = (
        df.groupby("ProductID", as_index=False)
        .agg(
            GrossGap=("GrossGap", "sum"),
            LostSales=("PotentialLostSalesUnits", "sum"),
            CMExposure=("CMExposure", "sum"),
            NetCM=("NetCMOpportunity", "sum"),
        )
        .sort_values("NetCM", ascending=False)
    )

    fig = px.bar(agg, x="ProductID", y="NetCM", title="فرصت خالص حاشیه مشارکت بر اساس محصول")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    show = [c for c in [
        "PeriodFa", "ProductID", "LineID", "OEE", "GrossGap", "InventoryAbsorbed",
        "RecoveredUnits", "SubstitutedUnits", "PotentialLostSalesUnits",
        "CMExposure", "ProtectedCM", "RecoveryCost", "NetCMOpportunity",
        "HoldingCost", "NetCM_after_Holding",
    ] if c in df.columns]
    st.dataframe(df[show].sort_values("NetCMOpportunity", ascending=False), use_container_width=True, height=420)


def page_sensitivity(sens, ship, impact, assumptions):
    st.header("تحلیل حساسیت")
    t1, t2, t3 = st.tabs(["نرخ بازیابی", "ارسال هماندوره", "WACC نگهداری (محلی)"])

    with t1:
        if sens.empty:
            st.warning("Sensitivity_RecoveryFrac.csv موجود نیست")
        else:
            st.dataframe(sens, use_container_width=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sens.RecoveryFrac, y=sens.ProtectedCM, name="حاشیه محافظتشده", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=sens.RecoveryFrac, y=sens.RecoveryCost, name="هزینه بازیابی", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=sens.RecoveryFrac, y=sens.NetCMOpportunity, name="فرصت خالص", mode="lines+markers"))
            fig.update_layout(xaxis_title="نرخ بازیابی", yaxis_title="دلار", height=400)
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        if ship.empty:
            st.warning("Sensitivity_SamePeriodShip.csv موجود نیست")
        else:
            st.dataframe(ship, use_container_width=True)
            fig = px.bar(ship, x="Label", y="TotalLostVsDemand", title="واحد ازدسترفته نسبت به تقاضای قطعی")
            st.plotly_chart(fig, use_container_width=True)

    with t3:
        if impact.empty or "HoldingCost" not in impact.columns:
            st.warning("ستون هزینه نگهداری در Impact نیست (موتور v1.7+ لازم است)")
        else:
            m = dict(zip(assumptions.Parameter.astype(str), assumptions.Value)) if len(assumptions) else {}
            base = float(m.get("HOLDING_COST_ANNUAL_WACC", 0.18))
            wacc = st.slider("نرخ سالانه نگهداری (WACC)", 0.05, 0.35, float(base), 0.01)
            scale = wacc / base if base else 1.0
            hold = float(impact.HoldingCost.sum()) * scale
            net = float(impact.NetCMOpportunity.sum())
            st.metric("فرصت خالص پایه", fmt_money(net))
            st.metric(f"هزینه نگهداری با WACC {wacc:.0%}", fmt_money(hold))
            st.metric("خالص پس از نگهداری", fmt_money(net - hold))
            st.caption("مقیاسدهی محلی و خطی نسبت به WACC — پایپلاین کامل دوباره اجرا نمیشود.")


def page_scenarios(scen: pd.DataFrame):
    st.header("نتایج سناریو")
    if scen.empty:
        st.warning("Scenario_Results.csv موجود نیست")
        return
    st.caption(
        "ستون NetCMImpact_after_RecoveryCost هویت متفاوتی از NetCMOpportunity پایه دارد "
        "(تفاوت در معرض CM منهای هزینه بازیابی سناریو)."
    )
    st.dataframe(scen, use_container_width=True)
    ycol = "NetCMImpact_after_RecoveryCost" if "NetCMImpact_after_RecoveryCost" in scen.columns else "CMImpact"
    fig = px.bar(scen, x="ScenarioID", y=ycol, color="ScenarioType", title=ycol)
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
