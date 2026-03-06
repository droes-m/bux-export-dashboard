from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.dashboard_data import build_portfolio_bundle, fmt_eur_short, render_data_source_sidebar

st.title("BUX Portfolio Dashboard")
st.caption("Multi-page analytics for portfolio performance, asset drilldowns, cashflows, forecasting, and mapping quality.")

tx, _master, security_map, source_label = render_data_source_sidebar(current_page="Home")
bundle = build_portfolio_bundle(tx, security_map)
metrics = bundle["metrics"]
portfolio_ts = bundle["portfolio_ts"]
coverage = bundle["coverage"]
anomalies = bundle["anomalies"]

st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Portfolio Value",
    fmt_eur_short(metrics.portfolio_value_eur),
    help="Current total value: cash balance + market value of mapped holdings (EUR).",
)
k2.metric(
    "Net External Flows",
    fmt_eur_short(metrics.net_external_flows_eur),
    help="Cumulative deposits minus withdrawals from transaction rows categorized as deposits.",
)
k3.metric(
    "Gain",
    fmt_eur_short(metrics.gain_after_all_cashflows_eur),
    delta=f"{metrics.gain_pct * 100:,.2f}%",
    help="Portfolio value minus net external flows. Includes current unrealized market impact.",
)
k4.metric(
    "Realized P/L",
    fmt_eur_short(metrics.realized_pnl_eur),
    help="Sum of realized Profit And Loss Amount from sell trades in the export.",
)

k5, k6, k7, k8 = st.columns(4)
k5.metric("Cash", fmt_eur_short(metrics.cash_balance_eur), help="Latest reported cash balance in EUR.")
k6.metric(
    "Market Value",
    fmt_eur_short(metrics.market_value_eur),
    help="Marked-to-market value of mapped holdings, converted to EUR where needed.",
)
k7.metric(
    "Fees",
    fmt_eur_short(metrics.fees_eur),
    help="Cumulative fees from transaction category `fees`.",
)
k8.metric(
    "Taxes",
    fmt_eur_short(metrics.taxes_eur),
    help="Cumulative taxes from transaction category `tax`.",
)

c1, c2 = st.columns([2, 1])
with c1:
    st.subheader("Portfolio vs External Flows")
    line_df = portfolio_ts[["date", "portfolio_value_eur", "net_external_flows_eur", "gain_eur"]].copy()
    fig = px.line(
        line_df,
        x="date",
        y=["portfolio_value_eur", "net_external_flows_eur", "gain_eur"],
        labels={"value": "EUR", "variable": "Series", "date": "Date"},
    )
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Workspace Status")
    st.write(f"Mapped holdings coverage: **{coverage:.0%}**")
    st.write(f"Valuation anomalies: **{len(anomalies)}**")
    if coverage < 0.9:
        st.warning("Coverage below 90%: valuation can be partial.")
    if not anomalies.empty:
        st.error("Anomalies detected. Review Mapping & QA page.")
