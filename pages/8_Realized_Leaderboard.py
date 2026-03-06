from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard_data import fmt_eur_short, render_data_source_sidebar

st.set_page_config(page_title="Realized Leaderboard", layout="wide")
st.title("Realized Leaderboard")
st.caption("Portfolio-wide realized performance by asset (moving-average cost basis estimate).")

tx, master, _security_map, source_label = render_data_source_sidebar(current_page="Realized Leaderboard")
st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

assets = sorted(master["asset_name"].dropna().unique().tolist())


def realized_stats_for_asset(asset_tx: pd.DataFrame) -> dict:
    qty = 0.0
    cost = 0.0
    realized_cost = 0.0
    realized_proceeds = 0.0

    for _, r in asset_tx.sort_values("date").iterrows():
        q = float(r.get("signed_quantity", 0.0) or 0.0)
        p = float(r.get("Asset Price", np.nan))
        if q > 0 and pd.notna(p):
            qty += q
            cost += q * p
        elif q < 0 and qty > 0 and pd.notna(p):
            sell_qty = min(-q, qty)
            avg_cost = cost / qty if qty > 0 else 0.0
            realized_cost += avg_cost * sell_qty
            realized_proceeds += p * sell_qty
            cost -= avg_cost * sell_qty
            qty -= sell_qty
            if qty <= 1e-12:
                qty = 0.0
                cost = 0.0

    realized_pnl_est = realized_proceeds - realized_cost
    realized_pct = (realized_pnl_est / realized_cost) if realized_cost > 1e-12 else np.nan
    return {
        "realized_cost_ccy": realized_cost,
        "realized_proceeds_ccy": realized_proceeds,
        "realized_pnl_est_ccy": realized_pnl_est,
        "realized_pct_est": realized_pct,
    }


rows = []
for asset in assets:
    asset_tx = tx[tx["Asset Name"].eq(asset)].copy()
    if asset_tx.empty:
        continue

    sells = asset_tx[asset_tx["Transaction Type"].eq("Sell Trade")]
    realized_rows = sells["Profit And Loss Amount"].fillna(0.0)
    realized_pnl_eur = float(realized_rows.sum()) if not realized_rows.empty else 0.0
    sell_count = int(len(sells))

    stats = realized_stats_for_asset(asset_tx)
    asset_ccy = ""
    if asset_tx["Asset Currency"].dropna().any():
        asset_ccy = str(asset_tx["Asset Currency"].dropna().iloc[0])

    rows.append(
        {
            "asset_name": asset,
            "asset_currency": asset_ccy,
            "sell_trades": sell_count,
            "realized_pnl_eur": realized_pnl_eur,
            "realized_pct_est": stats["realized_pct_est"],
            "realized_cost_ccy": stats["realized_cost_ccy"],
            "realized_pnl_est_ccy": stats["realized_pnl_est_ccy"],
        }
    )

leader = pd.DataFrame(rows)
leader = leader[leader["sell_trades"] > 0].copy()
if leader.empty:
    st.info("No sold positions yet, so no realized leaderboard is available.")
    st.stop()

min_cost = st.slider("Min sold cost basis (asset ccy)", min_value=0, max_value=5000, value=250, step=50)
show_top_n = st.slider("Top/Bottom assets to show", min_value=3, max_value=min(20, len(leader)), value=min(8, len(leader)))

filt = leader[leader["realized_cost_ccy"] >= float(min_cost)].copy()
if filt.empty:
    st.warning("No assets pass the current minimum sold cost basis filter.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Assets with realized trades",
    f"{len(filt)}",
    help="Count of assets with at least one sell and passing the minimum sold-cost filter.",
)
k2.metric(
    "Realized P/L (EUR total)",
    fmt_eur_short(float(filt["realized_pnl_eur"].sum())),
    help="Total realized P/L in EUR, using BUX Profit And Loss Amount where available.",
)
k3.metric(
    "Median realized %",
    f"{filt['realized_pct_est'].median() * 100:,.2f}%",
    help="Median estimated realized return % across filtered assets (moving-average cost basis).",
)
k4.metric(
    "Win rate (realized % > 0)",
    f"{(filt['realized_pct_est'] > 0).mean() * 100:,.1f}%",
    help="Share of filtered assets with positive estimated realized return.",
)

best_pct = filt.sort_values("realized_pct_est", ascending=False).head(show_top_n)
worst_pct = filt.sort_values("realized_pct_est", ascending=True).head(show_top_n)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Best Realized %")
    st.dataframe(
        best_pct[["asset_name", "realized_pct_est", "realized_pnl_eur", "sell_trades", "realized_cost_ccy"]],
        use_container_width=True,
        hide_index=True,
    )
with c2:
    st.subheader("Worst Realized %")
    st.dataframe(
        worst_pct[["asset_name", "realized_pct_est", "realized_pnl_eur", "sell_trades", "realized_cost_ccy"]],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Realized % by Asset")
chart = filt.sort_values("realized_pct_est", ascending=False).copy()
fig_pct = px.bar(
    chart,
    x="asset_name",
    y="realized_pct_est",
    color="realized_pct_est",
    color_continuous_scale="RdYlGn",
    labels={"realized_pct_est": "Realized %", "asset_name": "Asset"},
)
fig_pct.update_yaxes(tickformat=".1%")
st.plotly_chart(fig_pct, use_container_width=True)

st.subheader("Realized P/L (EUR) by Asset")
fig_pnl = px.bar(
    chart.sort_values("realized_pnl_eur", ascending=False),
    x="asset_name",
    y="realized_pnl_eur",
    color="realized_pnl_eur",
    color_continuous_scale="RdYlGn",
    labels={"realized_pnl_eur": "EUR", "asset_name": "Asset"},
)
st.plotly_chart(fig_pnl, use_container_width=True)

st.subheader("Full Table")
out = chart.copy()
out["realized_pct_est"] = out["realized_pct_est"] * 100.0
out = out.rename(columns={"realized_pct_est": "realized_pct_est_%"})
st.dataframe(out.sort_values("realized_pct_est_%", ascending=False), use_container_width=True, hide_index=True)

st.caption(
    "Realized % is estimated using moving-average cost basis from transaction prices. "
    "Realized P/L in EUR uses BUX export `Profit And Loss Amount` where available."
)
