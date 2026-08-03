"""
Budget Variance Analyzer
Compare budgeted vs. actual spending, classify variances, forecast year-end.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader     import load_csv, load_sample
from src.variance_engine import compute_variance, forecast_year_end, STATUS_COLOR
from src.reporter        import (
    department_summary, category_summary, monthly_trend,
    top_variances, portfolio_kpis,
)

st.set_page_config(
    page_title="Budget Variance Analyzer",
    page_icon="$",
    layout="wide",
)

NAVY = "#1B2A4A"
BLUE = "#2E5FA3"
FONT = dict(family="Inter, Segoe UI, sans-serif", color="#333333")


def base_layout(title: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=14, color=NAVY)),
        plot_bgcolor="white", paper_bgcolor="white", font=FONT,
        margin=dict(l=40, r=20, t=48, b=40),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#EEEEEE", zeroline=False),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25),
    )


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Budget Variance Analyzer")
    st.markdown("---")

    use_sample = st.toggle("Use sample data", value=True)
    uploaded = None
    if not use_sample:
        uploaded = st.file_uploader("Upload budget CSV", type=["csv"])

    st.markdown("---")
    st.subheader("Filters")


# ── Load data ────────────────────────────────────────────────────────────────────
@st.cache_data
def get_sample():
    return load_sample()


try:
    if use_sample:
        raw = get_sample()
    elif uploaded:
        raw = load_csv(uploaded)
    else:
        st.info("Upload a CSV or enable sample data to begin.")
        st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()

# Sidebar filters
all_depts = sorted(raw["department"].unique())
all_cats  = sorted(raw["category"].unique())

with st.sidebar:
    sel_depts = st.multiselect("Department", all_depts, default=all_depts)
    sel_cats  = st.multiselect("Category",   all_cats,  default=all_cats)

mask = (
    raw["department"].isin(sel_depts) &
    raw["category"].isin(sel_cats)
)
df = raw[mask].copy()

if df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

enriched = compute_variance(df)
kpis     = portfolio_kpis(df)


# ── Header ────────────────────────────────────────────────────────────────────────
st.header("Budget Variance Analyzer")
months_label = f"{kpis['months_with_actuals']} of {kpis['total_months']} months with actuals"
st.caption(months_label)

st.markdown("---")

# ── KPI tiles ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
variance_sign = "+" if kpis["total_variance"] >= 0 else ""
c1.metric("Total Budget (YTD)",   f"${kpis['total_budget']:,.0f}")
c2.metric("Total Actual (YTD)",   f"${kpis['total_actual']:,.0f}")
c3.metric("Variance (YTD)",
          f"{variance_sign}${kpis['total_variance']:,.0f}",
          f"{variance_sign}{kpis['variance_pct']:.1%}")
c4.metric("Lines On/Under Budget",
          f"{kpis['n_favorable'] + kpis['n_on_budget']}",
          f"{kpis['n_warning']} warning / {kpis['n_critical']} critical",
          delta_color="off")
c5.metric("Coverage", f"{kpis['months_with_actuals']}/{kpis['total_months']} months")

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Monthly Trend", "By Department", "By Category", "Year-End Forecast", "Line Items"
])


# ── Tab 1: Monthly trend ───────────────────────────────────────────────────────────
with tab1:
    trend = monthly_trend(df)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=trend["month"], y=trend["budgeted"],
        name="Budgeted", marker_color=BLUE, opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=trend["month"], y=trend["actual"],
        name="Actual", mode="lines+markers",
        line=dict(color="#E74C3C", width=2), marker=dict(size=6),
        connectgaps=False,
    ))
    fig.update_layout(**base_layout("Monthly Budget vs. Actual Spend"))
    fig.update_yaxes(tickformat="$,.0f")
    st.plotly_chart(fig, use_container_width=True)

    # Variance waterfall
    has_data = trend.dropna(subset=["actual"])
    colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in has_data["variance"]]
    fig_var = go.Figure(go.Bar(
        x=has_data["month"], y=has_data["variance"],
        marker_color=colors, name="Variance (Budget − Actual)",
    ))
    fig_var.add_hline(y=0, line_color="#AAAAAA", line_dash="dash")
    fig_var.update_layout(**base_layout("Monthly Variance (+ = Under Budget)"))
    fig_var.update_yaxes(tickformat="$,.0f")
    st.plotly_chart(fig_var, use_container_width=True)


# ── Tab 2: By department ───────────────────────────────────────────────────────────
with tab2:
    dept = department_summary(df)

    col_l, col_r = st.columns([1, 2])
    with col_l:
        def color_status_cell(val):
            return f"color: {STATUS_COLOR.get(val, '#333')}; font-weight: bold"
        st.dataframe(
            dept.style
                .map(color_status_cell, subset=["status"])
                .format({
                    "budgeted":     "${:,.0f}",
                    "actual":       "${:,.0f}",
                    "variance":     "${:+,.0f}",
                    "variance_pct": "{:+.1%}",
                }),
            use_container_width=True, height=320,
        )
    with col_r:
        fig_dept = go.Figure()
        fig_dept.add_trace(go.Bar(
            x=dept["department"], y=dept["budgeted"],
            name="Budgeted", marker_color=BLUE, opacity=0.65,
        ))
        fig_dept.add_trace(go.Bar(
            x=dept["department"], y=dept["actual"],
            name="Actual",
            marker_color=[STATUS_COLOR.get(s, "#888") for s in dept["status"]],
        ))
        fig_dept.update_layout(
            **base_layout("Budget vs. Actual by Department"),
            barmode="group",
        )
        fig_dept.update_yaxes(tickformat="$,.0f")
        st.plotly_chart(fig_dept, use_container_width=True)


# ── Tab 3: By category ─────────────────────────────────────────────────────────────
with tab3:
    cat = category_summary(df)

    fig_cat = px.bar(
        cat.sort_values("variance"),
        x="variance", y="category", orientation="h",
        color="status",
        color_discrete_map=STATUS_COLOR,
        labels={"variance": "Variance ($)", "category": ""},
        title="Variance by Category (+ = Under Budget, − = Over Budget)",
    )
    fig_cat.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", font=FONT,
        margin=dict(l=10, r=20, t=48, b=30),
        xaxis=dict(tickformat="$+,.0f", showgrid=True, gridcolor="#EEEEEE"),
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=-0.15),
    )
    fig_cat.add_vline(x=0, line_color="#AAAAAA", line_dash="dash")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.dataframe(
        cat.style
            .map(color_status_cell, subset=["status"])
            .format({
                "budgeted":     "${:,.0f}",
                "actual":       "${:,.0f}",
                "variance":     "${:+,.0f}",
                "variance_pct": "{:+.1%}",
            }),
        use_container_width=True,
    )


# ── Tab 4: Year-end forecast ───────────────────────────────────────────────────────
with tab4:
    st.subheader("Year-End Forecast (based on YTD run rate)")
    forecast = forecast_year_end(df)

    # Department roll-up
    dept_fc = (
        forecast.groupby("department", as_index=False)
        .agg(
            full_year_budget=("full_year_budget", "sum"),
            actual_ytd      =("actual_ytd",       "sum"),
            forecast_year_end=("forecast_year_end","sum"),
        )
    )
    dept_fc["forecast_variance"]     = dept_fc["full_year_budget"] - dept_fc["forecast_year_end"]
    dept_fc["forecast_variance_pct"] = dept_fc["forecast_variance"] / dept_fc["full_year_budget"]

    fig_fc = go.Figure()
    fig_fc.add_trace(go.Bar(
        x=dept_fc["department"], y=dept_fc["full_year_budget"],
        name="Full-Year Budget", marker_color=BLUE, opacity=0.55,
    ))
    fig_fc.add_trace(go.Bar(
        x=dept_fc["department"], y=dept_fc["forecast_year_end"],
        name="Forecasted Spend",
        marker_color=["#E74C3C" if v < 0 else "#2ECC71"
                      for v in dept_fc["forecast_variance"]],
        opacity=0.85,
    ))
    fig_fc.update_layout(
        **base_layout("Full-Year Budget vs. Forecasted Spend by Department"),
        barmode="group",
    )
    fig_fc.update_yaxes(tickformat="$,.0f")
    st.plotly_chart(fig_fc, use_container_width=True)

    def color_fc_variance(val):
        if not isinstance(val, (int, float)) or pd.isna(val):
            return ""
        return f"color: {'#2ECC71' if val >= 0 else '#E74C3C'}; font-weight: bold"

    st.dataframe(
        dept_fc.style
            .map(color_fc_variance, subset=["forecast_variance"])
            .format({
                "full_year_budget":      "${:,.0f}",
                "actual_ytd":            "${:,.0f}",
                "forecast_year_end":     "${:,.0f}",
                "forecast_variance":     "${:+,.0f}",
                "forecast_variance_pct": "{:+.1%}",
            }),
        use_container_width=True,
    )


# ── Tab 5: Line item detail ────────────────────────────────────────────────────────
with tab5:
    st.subheader("All Budget Lines")

    show_cols = ["month", "department", "category", "budgeted",
                 "actual", "variance", "variance_pct", "status"]
    line_df = enriched[[c for c in show_cols if c in enriched.columns]].copy()
    line_df["month"] = line_df["month"].dt.strftime("%Y-%m")

    status_filter = st.multiselect(
        "Filter by status", options=list(STATUS_COLOR.keys()),
        default=list(STATUS_COLOR.keys()),
    )
    line_df = line_df[line_df["status"].isin(status_filter)]

    st.dataframe(
        line_df.style
            .map(color_status_cell, subset=["status"])
            .format({
                "budgeted":     "${:,.0f}",
                "actual":       "${:,.0f}",
                "variance":     "${:+,.0f}",
                "variance_pct": "{:+.1%}",
            }, na_rep="—"),
        use_container_width=True, height=500,
    )

    st.download_button(
        "Download Line Items (.csv)",
        enriched.to_csv(index=False),
        "budget_variance.csv", "text/csv",
    )
