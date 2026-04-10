from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard_data import build_portfolio_bundle, fmt_eur_short, render_data_source_sidebar

st.set_page_config(page_title="Reconciliation", layout="wide")
st.title("Reconciliation")
st.caption("Compare dashboard valuation/gain against your current BUX app values.")

tx, _master, security_map, source_label = render_data_source_sidebar()
bundle = build_portfolio_bundle(tx, security_map)
metrics = bundle["metrics"]
portfolio_ts = bundle["portfolio_ts"]
holdings_ts = bundle["holdings_ts"]
asset_value_ts = bundle["asset_value_ts"]
effective_mapping = bundle["effective_mapping"]

st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

c1, c2 = st.columns(2)
with c1:
    bux_value = st.number_input("BUX portfolio value (EUR)", min_value=0.0, value=21824.53, step=10.0, format="%.2f")
with c2:
    bux_gain = st.number_input("BUX gain (EUR)", value=3974.53, step=10.0, format="%.2f")

app_value = metrics.portfolio_value_eur
app_gain = metrics.gain_after_all_cashflows_eur

expected_base = bux_value - bux_gain
app_base = metrics.net_external_flows_eur

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "App Value",
    fmt_eur_short(app_value),
    delta=fmt_eur_short(app_value - bux_value),
    help="Dashboard-calculated portfolio value. Delta is app value minus entered BUX value.",
)
k2.metric("BUX Value", fmt_eur_short(bux_value), help="Manual value you entered from the BUX app.")
k3.metric(
    "App Gain",
    fmt_eur_short(app_gain),
    delta=fmt_eur_short(app_gain - bux_gain),
    help="Dashboard gain = app value - app net external flows. Delta is app gain minus entered BUX gain.",
)
k4.metric("BUX Gain", fmt_eur_short(bux_gain), help="Manual gain you entered from the BUX app.")

s1, s2 = st.columns(2)
with s1:
    st.write(f"Implied BUX base (`value - gain`): **EUR {expected_base:,.2f}**")
with s2:
    st.write(f"App base (`net_external_flows`): **EUR {app_base:,.2f}**")

st.subheader("Gap Summary")
summary = pd.DataFrame(
    [
        {"metric": "value_gap", "eur": app_value - bux_value},
        {"metric": "gain_gap", "eur": app_gain - bux_gain},
        {"metric": "base_gap", "eur": app_base - expected_base},
    ]
)
st.dataframe(summary, use_container_width=True, hide_index=True)

st.subheader("Current Holdings Contribution")
if holdings_ts.empty or asset_value_ts.empty:
    st.info("No holdings/value data available.")
else:
    h = holdings_ts.iloc[-1].drop(labels=["date"]).rename("quantity").reset_index()
    h = h.rename(columns={h.columns[0]: "asset_id"})
    h = h[h["quantity"].abs() > 1e-9]
    v = asset_value_ts.iloc[-1].drop(labels=["date"]).rename("value_eur").reset_index()
    v = v.rename(columns={v.columns[0]: "asset_id"})
    out = h.merge(v, on="asset_id", how="left").merge(
        effective_mapping[["asset_id", "asset_name", "ticker", "confidence", "source"]],
        on="asset_id",
        how="left",
    )
    out["weight"] = out["value_eur"] / out["value_eur"].sum()
    st.dataframe(out.sort_values("value_eur", ascending=False), use_container_width=True, hide_index=True)

st.subheader("Timeline At Export Date")
export_end = tx["date"].max()
snap = portfolio_ts[portfolio_ts["date"] <= export_end].tail(1)
if not snap.empty:
    row = snap.iloc[0]
    st.write(
        f"At export end `{export_end.date()}`: value **EUR {row['portfolio_value_eur']:,.2f}**, "
        f"net external flows **EUR {row['net_external_flows_eur']:,.2f}**, gain **EUR {row['gain_eur']:,.2f}**"
    )
