from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard_data import render_data_source_sidebar

st.set_page_config(page_title="Transactions Explorer", layout="wide")
st.title("Transactions Explorer")

tx, master, _security_map, source_label = render_data_source_sidebar()
st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

c1, c2, c3 = st.columns(3)
with c1:
    categories = sorted(tx["Transaction Category"].dropna().unique().tolist())
    cat_filter = st.multiselect("Category", categories, default=categories)
with c2:
    assets = sorted(master["asset_name"].dropna().unique().tolist())
    asset_filter = st.multiselect("Asset", assets)
with c3:
    ccy = sorted(tx["Transaction Currency"].dropna().unique().tolist())
    ccy_filter = st.multiselect("Transaction Currency", ccy, default=ccy)

min_date = tx["date"].min().date()
max_date = tx["date"].max().date()
date_range = st.slider("Date range", min_value=min_date, max_value=max_date, value=(min_date, max_date))

filtered = tx[tx["Transaction Category"].isin(cat_filter)]
filtered = filtered[filtered["Transaction Currency"].isin(ccy_filter)]
if asset_filter:
    filtered = filtered[filtered["Asset Name"].isin(asset_filter)]
filtered = filtered[(filtered["date"].dt.date >= date_range[0]) & (filtered["date"].dt.date <= date_range[1])]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Rows", f"{len(filtered):,}", help="Number of transactions after current filters.")
k2.metric(
    "Transaction Amount Sum",
    f"{filtered['Transaction Amount'].fillna(0).sum():,.2f}",
    help="Sum of Transaction Amount across filtered rows (native sign from export).",
)
k3.metric(
    "Fees Sum",
    f"{filtered.loc[filtered['Transaction Category'].eq('fees'),'Transaction Amount'].fillna(0).sum():,.2f}",
    help="Sum of filtered fee transactions.",
)
k4.metric(
    "Taxes Sum",
    f"{filtered.loc[filtered['Transaction Category'].eq('tax'),'Transaction Amount'].fillna(0).sum():,.2f}",
    help="Sum of filtered tax transactions.",
)

st.subheader("Filtered Timeline")
series = filtered.groupby("date", as_index=False)["Transaction Amount"].sum().sort_values("date")
if series.empty:
    st.info("No rows under current filters.")
else:
    fig = px.bar(series, x="date", y="Transaction Amount", labels={"Transaction Amount": "EUR/CCY", "date": "Date"})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Filtered Ledger")
st.dataframe(filtered.sort_values("Transaction Time (CET)", ascending=False), use_container_width=True, hide_index=True)

csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered transactions CSV",
    data=csv_bytes,
    file_name="filtered_transactions.csv",
    mime="text/csv",
)
