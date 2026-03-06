from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics import build_monthly_performance_view
from src.dashboard_data import build_portfolio_bundle, fmt_eur_short, render_data_source_sidebar

st.set_page_config(page_title="Overview", layout="wide")
st.title("Overview")

tx, master, security_map, source_label = render_data_source_sidebar(current_page="Overview")
bundle = build_portfolio_bundle(tx, security_map)
portfolio_ts = bundle["portfolio_ts"].copy()
holdings_ts = bundle["holdings_ts"].copy()
asset_value_ts = bundle["asset_value_ts"].copy()
metrics = bundle["metrics"]

st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Portfolio",
    fmt_eur_short(metrics.portfolio_value_eur),
    help="Current total value: cash + market value of mapped holdings (EUR).",
)
k2.metric(
    "Gain",
    fmt_eur_short(metrics.gain_after_all_cashflows_eur),
    delta=f"{metrics.gain_pct * 100:,.2f}%",
    help="Portfolio value minus net external flows.",
)
k3.metric(
    "External Flows",
    fmt_eur_short(metrics.net_external_flows_eur),
    help="Cumulative deposits minus withdrawals.",
)
k4.metric(
    "Market",
    fmt_eur_short(metrics.market_value_eur),
    help="Current marked-to-market value of holdings.",
)

k5, _ = st.columns([1, 3])
k5.metric("Cash", fmt_eur_short(metrics.cash_balance_eur), help="Latest cash balance in EUR.")

st.subheader("Performance Timeline")
line_df = portfolio_ts[["date", "portfolio_value_eur", "net_external_flows_eur", "gain_eur"]].copy()
fig_perf = px.line(
    line_df,
    x="date",
    y=["portfolio_value_eur", "net_external_flows_eur", "gain_eur"],
    labels={"value": "EUR", "variable": "Series", "date": "Date"},
)
fig_perf.update_layout(legend_title_text="")
st.plotly_chart(fig_perf, use_container_width=True)

st.subheader("Monthly Market Result vs Deposits")
st.caption(
    "Monthly market result strips out net deposits/withdrawals. Positive bars mean the portfolio gained value beyond cash you added."
)
monthly_perf = build_monthly_performance_view(portfolio_ts, months=12)

mc1, mc2, mc3 = st.columns(3)
mc1.metric(
    "Market Result (12M)",
    fmt_eur_short(float(monthly_perf["market_result_eur"].sum())) if not monthly_perf.empty else fmt_eur_short(0.0),
    help="Sum of monthly portfolio change after removing net external flows.",
)
mc2.metric(
    "Deposits / Withdrawals (12M)",
    fmt_eur_short(float(monthly_perf["external_flow_eur"].sum())) if not monthly_perf.empty else fmt_eur_short(0.0),
    help="Net external cash added over the same 12-month window.",
)
mc3.metric(
    "Portfolio Change (12M)",
    fmt_eur_short(float(monthly_perf["portfolio_change_eur"].sum())) if not monthly_perf.empty else fmt_eur_short(0.0),
    help="Total change in portfolio value over the same 12-month window.",
)

if monthly_perf.empty:
    st.info("Not enough timeline data for a monthly performance breakdown.")
else:
    market_colors = ["#ff4d73" if value >= 0 else "#7a1730" for value in monthly_perf["market_result_eur"]]
    fig_market = go.Figure()
    fig_market.add_bar(
        x=monthly_perf["month_label"],
        y=monthly_perf["market_result_eur"],
        name="Market result",
        marker_color=market_colors,
        text=[f"{value:,.0f} EUR" for value in monthly_perf["market_result_eur"]],
        textposition="outside",
        hovertemplate="%{x}<br>Market result: %{y:,.2f} EUR<extra></extra>",
    )
    fig_market.add_scatter(
        x=monthly_perf["month_label"],
        y=monthly_perf["external_flow_eur"],
        name="Net deposits",
        mode="lines+markers",
        line=dict(color="#6c757d", width=2),
        marker=dict(size=7),
        hovertemplate="%{x}<br>Net deposits: %{y:,.2f} EUR<extra></extra>",
    )
    fig_market.update_layout(
        yaxis_title="EUR",
        xaxis_title="Month",
        legend_title_text="",
        bargap=0.25,
    )
    st.plotly_chart(fig_market, use_container_width=True)

    with st.expander("Monthly breakdown", expanded=False):
        st.dataframe(
            monthly_perf[["month_label", "portfolio_change_eur", "external_flow_eur", "market_result_eur"]].rename(
                columns={
                    "month_label": "Month",
                    "portfolio_change_eur": "Portfolio change (EUR)",
                    "external_flow_eur": "Net deposits (EUR)",
                    "market_result_eur": "Market result (EUR)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

c1, c2 = st.columns(2)
with c1:
    st.subheader("Drawdown")
    dd = portfolio_ts[["date", "portfolio_value_eur"]].copy()
    dd["peak"] = dd["portfolio_value_eur"].cummax()
    dd["drawdown_pct"] = (dd["portfolio_value_eur"] / dd["peak"]) - 1.0
    fig_dd = px.area(dd, x="date", y="drawdown_pct", labels={"drawdown_pct": "Drawdown", "date": "Date"})
    fig_dd.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig_dd, use_container_width=True)

with c2:
    st.subheader("Monthly Net Change")
    month = build_monthly_performance_view(portfolio_ts, months=0)
    fig_mc = px.bar(
        month,
        x="month_label",
        y="portfolio_change_eur",
        labels={"portfolio_change_eur": "EUR", "month_label": "Month"},
    )
    st.plotly_chart(fig_mc, use_container_width=True)

st.subheader("Current Allocation")
if holdings_ts.empty or asset_value_ts.empty:
    st.info("No holdings/valuation data available.")
else:
    latest_holdings = holdings_ts.iloc[-1].drop(labels=["date"]).rename("quantity").reset_index()
    latest_holdings = latest_holdings.rename(columns={latest_holdings.columns[0]: "asset_id"})
    latest_holdings = latest_holdings[latest_holdings["quantity"].abs() > 1e-9]

    latest_values = asset_value_ts.iloc[-1].drop(labels=["date"]).rename("value_eur").reset_index()
    latest_values = latest_values.rename(columns={latest_values.columns[0]: "asset_id"})

    snapshot = latest_holdings.merge(
        security_map[["asset_id", "asset_name", "ticker", "asset_currency"]], on="asset_id", how="left"
    ).merge(latest_values, on="asset_id", how="left")
    snapshot["weight"] = snapshot["value_eur"] / snapshot["value_eur"].sum()

    cc1, cc2 = st.columns([1, 1])
    with cc1:
        fig_alloc = px.pie(snapshot, values="value_eur", names="asset_name")
        st.plotly_chart(fig_alloc, use_container_width=True)
    with cc2:
        st.dataframe(
            snapshot.sort_values("value_eur", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

st.subheader("Rolling Return")
roll = portfolio_ts[["date", "portfolio_value_eur"]].copy()
roll["ret_30d"] = roll["portfolio_value_eur"].pct_change(30)
roll["ret_90d"] = roll["portfolio_value_eur"].pct_change(90)
fig_roll = px.line(roll, x="date", y=["ret_30d", "ret_90d"], labels={"value": "Return", "date": "Date"})
fig_roll.update_yaxes(tickformat=".1%")
fig_roll.update_layout(legend_title_text="")
st.plotly_chart(fig_roll, use_container_width=True)

st.caption(
    "Overview focuses on valuation trajectory, allocation, and risk shape. "
    "Use Asset Drilldown and Forecast pages for deeper diagnostics."
)
