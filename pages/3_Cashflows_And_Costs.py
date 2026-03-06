from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard_data import build_portfolio_bundle, fmt_eur_short, render_data_source_sidebar

st.set_page_config(page_title="Cashflows & Costs", layout="wide")
st.title("Cashflows & Costs")

tx, _master, security_map, source_label = render_data_source_sidebar()
bundle = build_portfolio_bundle(tx, security_map)
metrics = bundle["metrics"]

st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Net External Flows",
    fmt_eur_short(metrics.net_external_flows_eur),
    help="Cumulative deposits minus withdrawals.",
)
k2.metric(
    "Net Dividends",
    fmt_eur_short(metrics.dividends_net_eur),
    help="Sum of net dividend amounts from export rows.",
)
k3.metric(
    "Interest",
    fmt_eur_short(metrics.interest_eur),
    help="Cumulative interest transactions.",
)
k4.metric(
    "Fees + Taxes",
    fmt_eur_short(metrics.fees_eur + metrics.taxes_eur),
    help="Combined cumulative drag from fees and taxes.",
)

monthly = tx.copy()
monthly["month"] = monthly["date"].dt.to_period("M").astype(str)

st.subheader("Monthly Cashflow by Category")
monthly_cf = (
    monthly.groupby(["month", "Transaction Category"], as_index=False)["Transaction Amount"]
    .sum()
    .sort_values("month")
)
fig_cf = px.bar(monthly_cf, x="month", y="Transaction Amount", color="Transaction Category")
st.plotly_chart(fig_cf, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Cumulative Fee + Tax Drag")
    drag = tx[tx["Transaction Category"].isin(["fees", "tax"])].copy().sort_values("date")
    if drag.empty:
        st.info("No fee/tax rows.")
    else:
        drag_day = drag.groupby("date", as_index=False)["Transaction Amount"].sum()
        drag_day["cum_drag"] = drag_day["Transaction Amount"].cumsum()
        fig_drag = px.area(drag_day, x="date", y="cum_drag", labels={"cum_drag": "EUR", "date": "Date"})
        st.plotly_chart(fig_drag, use_container_width=True)

with c2:
    st.subheader("Income vs Costs (Monthly)")
    m = monthly.copy()
    m["income"] = 0.0
    m.loc[m["Transaction Category"].isin(["dividends", "interest"]), "income"] = m["Transaction Amount"].fillna(0.0)
    m["cost"] = 0.0
    m.loc[m["Transaction Category"].isin(["fees", "tax"]), "cost"] = m["Transaction Amount"].fillna(0.0)
    income_cost = m.groupby("month", as_index=False)[["income", "cost"]].sum().sort_values("month")
    fig_ic = px.bar(income_cost, x="month", y=["income", "cost"], barmode="group")
    st.plotly_chart(fig_ic, use_container_width=True)

st.subheader("Category Heatmap (Month x Category)")
pivot = monthly_cf.pivot(index="Transaction Category", columns="month", values="Transaction Amount").fillna(0.0)
if pivot.empty:
    st.info("No category/month data.")
else:
    heat_data = pivot.reset_index().melt(id_vars=["Transaction Category"], var_name="month", value_name="amount")
    fig_h = px.density_heatmap(
        heat_data,
        x="month",
        y="Transaction Category",
        z="amount",
        histfunc="avg",
        color_continuous_scale="RdBu",
    )
    st.plotly_chart(fig_h, use_container_width=True)

st.subheader("Cashflow Ledger")
cat_default = ["deposits", "dividends", "interest", "fees", "tax"]
selected = st.multiselect(
    "Categories",
    sorted(tx["Transaction Category"].dropna().unique().tolist()),
    default=[c for c in cat_default if c in tx["Transaction Category"].dropna().unique().tolist()],
)
filtered = tx[tx["Transaction Category"].isin(selected)]
st.dataframe(filtered.sort_values("Transaction Time (CET)", ascending=False), use_container_width=True, hide_index=True)
