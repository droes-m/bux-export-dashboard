from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard_data import (
    build_portfolio_bundle,
    fetch_security_overview_cached,
    fmt_eur_short,
    render_data_source_sidebar,
)

st.set_page_config(page_title="Asset Drilldown", layout="wide")
st.title("Asset Drilldown")

tx, master, security_map, source_label = render_data_source_sidebar(current_page="Asset Drilldown")
try:
    bundle = build_portfolio_bundle(tx, security_map)
except Exception as exc:
    st.error("Failed to build portfolio data bundle for drilldown.")
    st.exception(exc)
    st.stop()

holdings_ts = bundle["holdings_ts"].copy()
asset_value_ts = bundle["asset_value_ts"].copy()
prices_long = bundle["prices_long"].copy()
eurusd = bundle["eurusd"].copy()
effective_mapping = bundle["effective_mapping"].copy()

assets = sorted(master["asset_name"].dropna().unique().tolist())
if not assets:
    st.info("No assets found in this export.")
    st.stop()

selected_asset = st.selectbox("Select asset", assets)
asset_row = security_map[security_map["asset_name"].eq(selected_asset)].head(1)
if asset_row.empty:
    st.warning("Selected asset has no mapping row.")
    st.stop()

asset_id = asset_row["asset_id"].iloc[0]
ticker = asset_row["ticker"].iloc[0]
asset_ccy = asset_row["asset_currency"].iloc[0]

eff_row = effective_mapping[effective_mapping["asset_id"].eq(asset_id)].head(1)
if not eff_row.empty:
    ticker = eff_row["ticker"].iloc[0]
    asset_ccy = eff_row["asset_currency"].iloc[0]
    price_scale = float(eff_row["price_scale"].iloc[0])
else:
    price_scale = 1.0

st.caption(f"Source: `{source_label}` | Asset ID: `{asset_id}` | Ticker: `{ticker}` | Currency: `{asset_ccy}`")


def fmt_num(v, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    try:
        return f"{float(v):,.{digits}f}"
    except Exception:
        return str(v)


def fmt_pct(v, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except Exception:
        return str(v)


def fmt_big(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    try:
        n = float(v)
    except Exception:
        return str(v)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000_000_000:
        return f"{sign}{n / 1_000_000_000_000:.2f}T"
    if n >= 1_000_000_000:
        return f"{sign}{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{sign}{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{sign}{n / 1_000:.2f}k"
    return f"{sign}{n:,.0f}"


with st.expander("Security Fundamentals", expanded=False):
    if not str(ticker or "").strip():
        st.info("No ticker mapping for this asset yet.")
    else:
        sec = fetch_security_overview_cached(str(ticker))
        if not sec.get("ok", False):
            st.info(f"Fundamentals unavailable right now ({sec.get('error', 'unknown error')}).")
        else:
            s = sec.get("summary", {})
            kind = sec.get("kind", "unknown")
            st.caption(
                f"{s.get('name', ticker)} | Type: `{(s.get('quote_type') or kind).upper()}` | "
                f"Exchange: `{s.get('exchange', 'n/a')}` | Currency: `{s.get('currency', 'n/a')}`"
            )

            if kind == "etf":
                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Expense Ratio", fmt_pct(s.get("expense_ratio")), help="Reported fund expense ratio.")
                e2.metric("AUM / Total Assets", fmt_big(s.get("total_assets")), help="Total fund assets under management.")
                e3.metric("Yield", fmt_pct(s.get("yield")), help="Reported fund yield.")
                e4.metric("Category", s.get("category") or "n/a", help="Fund category/classification.")

                e5, e6, e7 = st.columns(3)
                e5.metric("Fund Family", s.get("fund_family") or "n/a")
                e6.metric("3Y Avg Return", fmt_pct(s.get("three_year_avg_return")))
                e7.metric("5Y Avg Return", fmt_pct(s.get("five_year_avg_return")))

                holdings = sec.get("top_holdings")
                st.subheader("Top Holdings")
                if isinstance(holdings, pd.DataFrame) and not holdings.empty:
                    st.dataframe(holdings.head(15), use_container_width=True, hide_index=True)
                else:
                    st.caption("Top holdings not available from current data source.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Market Cap", fmt_big(s.get("market_cap")), help="Equity market capitalization.")
                c2.metric("P/E (TTM)", fmt_num(s.get("pe_trailing")), help="Trailing price-to-earnings ratio.")
                c3.metric("Forward P/E", fmt_num(s.get("pe_forward")), help="Forward price-to-earnings estimate.")
                c4.metric("EPS (TTM)", fmt_num(s.get("eps_trailing")), help="Trailing earnings per share.")

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Revenue Growth", fmt_pct(s.get("revenue_growth")), help="Year-over-year revenue growth.")
                c6.metric("Operating Margin", fmt_pct(s.get("operating_margin")), help="Operating margin ratio.")
                c7.metric("Dividend Yield", fmt_pct(s.get("dividend_yield")), help="Dividend yield.")
                c8.metric("Beta", fmt_num(s.get("beta")), help="Beta vs market.")

                c9, c10 = st.columns(2)
                c9.metric("52W Low", fmt_num(s.get("fifty_two_week_low"), 2))
                c10.metric("52W High", fmt_num(s.get("fifty_two_week_high"), 2))

            text = str(s.get("summary_text", "") or "").strip()
            if text:
                st.subheader("Business / Fund Description")
                st.write(text)

asset_tx = tx[tx["Asset Id"].eq(asset_id)].copy().sort_values("date")
buys = asset_tx[asset_tx["Transfer Type"].eq("ASSET_TRADE_BUY")].copy()
sells = asset_tx[asset_tx["Transfer Type"].eq("ASSET_TRADE_SELL")].copy()

if asset_tx.empty:
    st.info("No transactions for this asset.")
    st.stop()

current_qty = float(asset_tx["signed_quantity"].sum())
realized_pnl = float(sells["Profit And Loss Amount"].fillna(0.0).sum()) if not sells.empty else 0.0
buy_qty = float(buys["Asset Quantity"].fillna(0.0).sum()) if not buys.empty else 0.0
avg_buy = float((buys["Asset Price"] * buys["Asset Quantity"]).sum() / buy_qty) if buy_qty > 0 else np.nan


def open_position_cost_basis(trades: pd.DataFrame) -> tuple[float, float]:
    qty = 0.0
    cost = 0.0
    for _, r in trades.sort_values("date").iterrows():
        q = float(r.get("signed_quantity", 0.0) or 0.0)
        p = float(r.get("Asset Price", np.nan))
        if q > 0 and pd.notna(p):
            qty += q
            cost += q * p
        elif q < 0 and qty > 0:
            sell_qty = min(-q, qty)
            avg_cost = cost / qty if qty > 0 else 0.0
            cost -= avg_cost * sell_qty
            qty -= sell_qty
            if qty <= 1e-12:
                qty = 0.0
                cost = 0.0
    avg_open = (cost / qty) if qty > 0 else np.nan
    return qty, avg_open


def realized_return_pct(trades: pd.DataFrame) -> tuple[float, float, float]:
    qty = 0.0
    cost = 0.0
    realized_cost = 0.0
    realized_proceeds = 0.0
    for _, r in trades.sort_values("date").iterrows():
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
    realized_pnl_ccy = realized_proceeds - realized_cost
    realized_pct = (realized_pnl_ccy / realized_cost) if realized_cost > 1e-12 else np.nan
    return realized_pct, realized_pnl_ccy, realized_cost


open_qty, open_avg_cost_ccy = open_position_cost_basis(asset_tx)
realized_pct, realized_pnl_ccy_est, realized_cost_ccy = realized_return_pct(asset_tx)

current_value = np.nan
implied_unit = np.nan
if not holdings_ts.empty and not asset_value_ts.empty and asset_id in holdings_ts.columns and asset_id in asset_value_ts.columns:
    current_value = float(asset_value_ts.iloc[-1][asset_id])
    qty_now = float(holdings_ts.iloc[-1][asset_id])
    if abs(qty_now) > 1e-9:
        implied_unit = current_value / qty_now

latest_unit_ccy = np.nan
if ticker and not prices_long.empty:
    p = prices_long[prices_long["ticker"].eq(ticker)].sort_values("date")
    if not p.empty:
        latest_unit_ccy = float(p["close"].iloc[-1]) * price_scale

eurusd_latest = np.nan
if not eurusd.empty:
    eurusd_latest = float(eurusd.sort_values("date")["eurusd"].iloc[-1])

unrealized_ccy = np.nan
unrealized_pct = np.nan
unrealized_eur = np.nan
open_avg_cost_eur = np.nan

if open_qty > 0 and pd.notna(open_avg_cost_ccy) and pd.notna(latest_unit_ccy):
    unrealized_ccy = (latest_unit_ccy - open_avg_cost_ccy) * open_qty
    base_cost = open_avg_cost_ccy * open_qty
    if abs(base_cost) > 1e-12:
        unrealized_pct = unrealized_ccy / base_cost

    if asset_ccy == "EUR":
        unrealized_eur = unrealized_ccy
        open_avg_cost_eur = open_avg_cost_ccy
    elif asset_ccy == "USD" and pd.notna(eurusd_latest) and eurusd_latest > 0:
        unrealized_eur = unrealized_ccy / eurusd_latest
        open_avg_cost_eur = open_avg_cost_ccy / eurusd_latest

k1, k2, k3, k4 = st.columns(4)
k1.metric("Current Qty", f"{current_qty:,.4f}", help="Net open quantity from cumulative buys and sells.")
k2.metric(
    "Current Value",
    fmt_eur_short(0.0 if pd.isna(current_value) else current_value),
    help="Latest estimated EUR value for this asset in the portfolio timeline.",
)
k3.metric(
    "Realized P/L",
    fmt_eur_short(realized_pnl),
    delta=None if pd.isna(realized_pct) else f"{realized_pct * 100:,.2f}%",
    help="Realized sell P/L in EUR from export rows; delta is estimated realized return on sold cost basis.",
)
k4.metric(
    f"Lifetime Avg Buy ({asset_ccy or 'ccy'})",
    "n/a" if pd.isna(avg_buy) else f"{avg_buy:,.4f}",
    help="Average unit price across all buy trades in history (ignores later sells).",
)
if not pd.isna(realized_pct):
    st.caption(
        f"Realized return estimate: {realized_pct * 100:,.2f}% on sold cost basis "
        f"({realized_pnl_ccy_est:,.2f} {asset_ccy} over {realized_cost_ccy:,.2f} {asset_ccy})."
    )

st.subheader("If Sold Now (Estimate)")
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric(
    "Open Qty Basis",
    f"{open_qty:,.4f}",
    help="Open quantity from moving-average cost-basis replay.",
)
s2.metric(
    f"Unrealized ({asset_ccy or 'asset ccy'})",
    "n/a" if pd.isna(unrealized_ccy) else f"{unrealized_ccy:,.2f}",
    delta=None if pd.isna(unrealized_pct) else f"{unrealized_pct * 100:,.2f}%",
    help="Estimated unrealized P/L on open quantity using latest mapped market price.",
)
s3.metric(
    "Unrealized (EUR)",
    "n/a" if pd.isna(unrealized_eur) else f"EUR {unrealized_eur:,.2f}",
    help="Unrealized P/L converted to EUR using latest FX when asset is not EUR.",
)
s4.metric(
    f"Mean Buy Price (Open, {asset_ccy or 'ccy'})",
    "n/a" if pd.isna(open_avg_cost_ccy) else f"{open_avg_cost_ccy:,.4f}",
    help="Open-position moving-average cost basis (BUX-style mean buy price).",
)
s5.metric(
    "Mean Buy Price (Open, EUR)",
    "n/a" if pd.isna(open_avg_cost_eur) else f"EUR {open_avg_cost_eur:,.4f}",
    help="Open-position moving-average cost basis converted to EUR.",
)
st.caption("Estimate uses moving-average cost basis on open quantity and latest mapped market price.")

st.subheader("Gain Over Time")
try:
    # Daily replay of position accounting for realized and unrealized P/L.
    replay = asset_tx.copy().sort_values("Transaction Time (CET)")
    end_candidates = [tx["date"].max(), pd.Timestamp.today().floor("D")]
    if ticker and not prices_long.empty:
        tpx = prices_long.loc[prices_long["ticker"].eq(ticker), "date"]
        if not tpx.empty:
            end_candidates.append(pd.to_datetime(tpx.max()).floor("D"))
    replay_end = max(end_candidates)
    replay_dates = pd.date_range(start=replay["date"].min(), end=replay_end, freq="D")
    by_day: dict[pd.Timestamp, pd.DataFrame] = {
        d: g for d, g in replay.groupby("date", sort=True)
    }

    qty = 0.0
    cost = 0.0
    realized_ccy_cum = 0.0
    realized_eur_cum = 0.0
    fx_on_day: dict[pd.Timestamp, float] = {}
    if asset_ccy == "USD" and not eurusd.empty:
        fx_series = (
            eurusd[["date", "eurusd"]]
            .dropna(subset=["eurusd"])
            .sort_values("date")
            .set_index("date")["eurusd"]
            .reindex(replay_dates)
            .ffill()
            .bfill()
        )
        fx_on_day = fx_series.to_dict()
    rows = []
    for d in replay_dates:
        day_rows = by_day.get(d, None)
        if day_rows is not None:
            for _, r in day_rows.iterrows():
                q = float(r.get("signed_quantity", 0.0) or 0.0)
                p = float(r.get("Asset Price", np.nan))
                if q > 0 and pd.notna(p):
                    qty += q
                    cost += q * p
                elif q < 0 and qty > 0 and pd.notna(p):
                    sell_qty = min(-q, qty)
                    avg_cost = cost / qty if qty > 0 else 0.0
                    realized_delta_ccy = (p - avg_cost) * sell_qty
                    realized_ccy_cum += realized_delta_ccy
                    pnl_eur_row = r.get("Profit And Loss Amount", np.nan)
                    if pd.notna(pnl_eur_row):
                        realized_eur_cum += float(pnl_eur_row)
                    elif asset_ccy == "EUR":
                        realized_eur_cum += realized_delta_ccy
                    elif asset_ccy == "USD":
                        fx = fx_on_day.get(d, np.nan)
                        if pd.notna(fx) and fx > 0:
                            realized_eur_cum += realized_delta_ccy / fx
                    cost -= avg_cost * sell_qty
                    qty -= sell_qty
                    if qty <= 1e-12:
                        qty = 0.0
                        cost = 0.0
        avg_cost_ccy = (cost / qty) if qty > 1e-12 else np.nan
        rows.append(
            {
                "date": d,
                "qty": qty,
                "avg_cost_ccy": avg_cost_ccy,
                "realized_ccy_cum": realized_ccy_cum,
                "realized_eur_cum": realized_eur_cum,
            }
        )

    gain_df = pd.DataFrame(rows)

    # Market unit price series in asset currency.
    if ticker and not prices_long.empty:
        p = prices_long[prices_long["ticker"].eq(ticker)][["date", "close"]].copy().sort_values("date")
        p["unit_ccy"] = p["close"] * price_scale
        p = p[["date", "unit_ccy"]]
        gain_df = gain_df.merge(p, on="date", how="left")
        gain_df["unit_ccy"] = gain_df["unit_ccy"].ffill()
    else:
        gain_df["unit_ccy"] = np.nan

    gain_df["unrealized_ccy"] = np.where(
        gain_df["qty"] > 1e-12,
        (gain_df["unit_ccy"] - gain_df["avg_cost_ccy"]) * gain_df["qty"],
        0.0,
    )
    gain_df["total_gain_ccy"] = gain_df["realized_ccy_cum"] + gain_df["unrealized_ccy"].fillna(0.0)
    gain_df["realized_eur_cum"] = gain_df["realized_eur_cum"].ffill().fillna(0.0)

    # Convert unrealized to EUR where possible; realized EUR is fixed at sell-time.
    if asset_ccy == "USD" and not eurusd.empty:
        fx = eurusd[["date", "eurusd"]].copy().sort_values("date")
        gain_df = gain_df.merge(fx, on="date", how="left")
        gain_df["eurusd"] = gain_df["eurusd"].ffill().bfill()
        gain_df["unrealized_eur"] = gain_df["unrealized_ccy"] / gain_df["eurusd"]
    else:
        gain_df["unrealized_eur"] = gain_df["unrealized_ccy"]
    gain_df["total_gain_eur"] = gain_df["realized_eur_cum"] + gain_df["unrealized_eur"].fillna(0.0)

    fig_gain = px.line(
        gain_df,
        x="date",
        y=["total_gain_eur", "realized_eur_cum", "unrealized_eur"],
        labels={"value": "EUR", "variable": "Series", "date": "Date"},
    )
    fig_gain.update_layout(legend_title_text="")
    st.plotly_chart(fig_gain, use_container_width=True)
except Exception:
    st.info("Gain-over-time chart unavailable for this asset with current mapping/data.")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Quantity Over Time")
    qty_hist = (
        asset_tx.groupby("date", as_index=False)["signed_quantity"].sum().sort_values("date")
    )
    qty_hist["cum_qty"] = qty_hist["signed_quantity"].cumsum()
    fig_qty = px.line(qty_hist, x="date", y="cum_qty", labels={"cum_qty": "Quantity", "date": "Date"})
    st.plotly_chart(fig_qty, use_container_width=True)

with c2:
    st.subheader("Value Over Time")
    if not asset_value_ts.empty and asset_id in asset_value_ts.columns:
        v = asset_value_ts[["date", asset_id]].rename(columns={asset_id: "value_eur"})
        fig_v = px.line(v, x="date", y="value_eur", labels={"value_eur": "EUR", "date": "Date"})
        st.plotly_chart(fig_v, use_container_width=True)
    else:
        st.info("No market value timeline for this asset (check mapping/prices).")

st.subheader("Asset Forecast")
if not ticker or prices_long.empty:
    st.info("No mapped market price series available for this asset forecast.")
else:
    price_hist = prices_long.loc[prices_long["ticker"].eq(ticker), ["date", "close"]].copy().sort_values("date")
    if price_hist.empty:
        st.info("No mapped market price series available for this asset forecast.")
    else:
        price_hist["unit_ccy"] = price_hist["close"] * price_scale
        price_hist = price_hist[["date", "unit_ccy"]].dropna()
        if len(price_hist) < 30:
            st.info("Need at least 30 price points to forecast this asset.")
        else:
            f1, f2, f3 = st.columns(3)
            with f1:
                af_method = st.selectbox(
                    "Forecast method (asset)",
                    ["Auto", "Linear", "Quadratic", "Exponential", "CAGR", "Flat"],
                    key=f"asset_fc_method_{asset_id}",
                )
            with f2:
                af_lookback = st.slider(
                    "Lookback window (days, asset)",
                    min_value=90,
                    max_value=2000,
                    value=600,
                    step=30,
                    key=f"asset_fc_lookback_{asset_id}",
                )
            with f3:
                af_horizon = st.slider(
                    "Forecast horizon (days, asset)",
                    min_value=30,
                    max_value=3650,
                    value=365,
                    step=30,
                    key=f"asset_fc_horizon_{asset_id}",
                )

            cutoff = price_hist["date"].max() - pd.Timedelta(days=af_lookback)
            fit_df = price_hist[price_hist["date"] >= cutoff].copy()
            if len(fit_df) < 20:
                fit_df = price_hist.tail(120).copy()

            fit_df["x"] = (fit_df["date"] - fit_df["date"].min()).dt.days.astype(float)
            x = fit_df["x"].to_numpy()
            y = fit_df["unit_ccy"].astype(float).to_numpy()

            def fit_linear(xv: np.ndarray, yv: np.ndarray) -> dict:
                coef = np.polyfit(xv, yv, deg=1)
                yhat = np.polyval(coef, xv)
                return {"name": "Linear", "coef": coef, "fit": yhat}

            def fit_quadratic(xv: np.ndarray, yv: np.ndarray) -> dict:
                coef = np.polyfit(xv, yv, deg=2)
                yhat = np.polyval(coef, xv)
                return {"name": "Quadratic", "coef": coef, "fit": yhat}

            def fit_exponential(xv: np.ndarray, yv: np.ndarray) -> dict | None:
                mask = yv > 0
                if mask.sum() < 20:
                    return None
                coef = np.polyfit(xv[mask], np.log(yv[mask]), deg=1)
                yhat = np.exp(np.polyval(coef, xv))
                return {"name": "Exponential", "coef": coef, "fit": yhat}

            def fit_cagr(xv: np.ndarray, yv: np.ndarray) -> dict | None:
                pos = yv > 0
                if pos.sum() < 2:
                    return None
                idx = np.where(pos)[0]
                i0, i1 = idx[0], idx[-1]
                days = max(float(xv[i1] - xv[i0]), 1.0)
                start_val = float(yv[i0])
                end_val = float(yv[i1])
                g = (end_val / start_val) ** (1.0 / days) - 1.0
                yhat = start_val * ((1.0 + g) ** (xv - xv[i0]))
                return {"name": "CAGR", "coef": np.array([g, start_val, xv[i0]]), "fit": yhat}

            def fit_flat(xv: np.ndarray, yv: np.ndarray) -> dict:
                yhat = np.full_like(yv, float(yv[-1]), dtype=float)
                return {"name": "Flat", "coef": np.array([float(yv[-1])]), "fit": yhat}

            def r2_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
                resid = y_true - y_pred
                rmse = float(np.sqrt(np.mean(resid**2)))
                ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
                r2 = float(1.0 - np.sum(resid**2) / ss_tot) if ss_tot > 1e-12 else 0.0
                return r2, rmse

            candidates: dict[str, dict] = {}
            for fn in [fit_linear, fit_quadratic, fit_flat]:
                m = fn(x, y)
                r2, rmse = r2_rmse(y, m["fit"])
                m.update({"r2": r2, "rmse": rmse})
                candidates[m["name"]] = m

            exp_m = fit_exponential(x, y)
            if exp_m is not None:
                r2, rmse = r2_rmse(y, exp_m["fit"])
                exp_m.update({"r2": r2, "rmse": rmse})
                candidates[exp_m["name"]] = exp_m

            cagr_m = fit_cagr(x, y)
            if cagr_m is not None:
                r2, rmse = r2_rmse(y, cagr_m["fit"])
                cagr_m.update({"r2": r2, "rmse": rmse})
                candidates[cagr_m["name"]] = cagr_m

            if af_method == "Auto":
                chosen = min(candidates.values(), key=lambda m: m["rmse"])
            elif af_method in candidates:
                chosen = candidates[af_method]
            else:
                chosen = candidates["Linear"]

            def predict(model: dict, xv: np.ndarray) -> np.ndarray:
                name = model["name"]
                coef = model["coef"]
                if name in ("Linear", "Quadratic"):
                    return np.polyval(coef, xv)
                if name == "Exponential":
                    return np.exp(np.polyval(coef, xv))
                if name == "CAGR":
                    g, start_val, x0 = coef
                    return start_val * ((1.0 + g) ** (xv - x0))
                return np.full_like(xv, float(coef[0]), dtype=float)

            fit_line = chosen["fit"]
            resid = y - fit_line
            resid_std = float(np.std(resid))

            last_date = fit_df["date"].max()
            future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=af_horizon, freq="D")
            future_x = (future_dates - fit_df["date"].min()).days.astype(float)
            future_pred = predict(chosen, future_x)

            forecast_df = pd.DataFrame({"date": future_dates, "forecast": future_pred})
            forecast_df["upper"] = forecast_df["forecast"] + resid_std
            forecast_df["lower"] = forecast_df["forecast"] - resid_std

            afk1, afk2, afk3 = st.columns(3)
            afk1.metric("Selected Model", chosen["name"], help="Model selected for market unit-price forecast.")
            afk2.metric("R2", f"{chosen['r2']:.3f}", help="Goodness of fit on selected lookback.")
            afk3.metric("RMSE", f"{chosen['rmse']:,.4f}", help=f"Root-mean-square fit error in {asset_ccy}.")

            fig_af = go.Figure()
            fig_af.add_trace(go.Scatter(x=price_hist["date"], y=price_hist["unit_ccy"], mode="lines", name="unit price history"))
            fig_af.add_trace(go.Scatter(x=fit_df["date"], y=fit_line, mode="lines", name=f"{chosen['name'].lower()} fit"))
            fig_af.add_trace(go.Scatter(x=forecast_df["date"], y=forecast_df["forecast"], mode="lines", name="unit price forecast"))
            fig_af.add_trace(
                go.Scatter(
                    x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
                    y=pd.concat([forecast_df["upper"], forecast_df["lower"][::-1]]),
                    fill="toself",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="±1σ band",
                    opacity=0.2,
                )
            )
            fig_af.update_layout(xaxis_title="Date", yaxis_title=f"Unit Price ({asset_ccy})")
            st.plotly_chart(fig_af, use_container_width=True)

            unit_now = float(price_hist["unit_ccy"].iloc[-1])
            unit_end = float(forecast_df["forecast"].iloc[-1])
            qty_for_projection = float(current_qty)
            if abs(qty_for_projection) < 1e-12:
                st.info("Current quantity is near zero, so projected position value is not meaningful.")
            else:
                eurusd_used = float(eurusd_latest) if (asset_ccy == "USD" and pd.notna(eurusd_latest) and eurusd_latest > 0) else np.nan
                if asset_ccy == "EUR":
                    value_now_eur = qty_for_projection * unit_now
                    value_end_eur = qty_for_projection * unit_end
                elif asset_ccy == "USD" and pd.notna(eurusd_used):
                    value_now_eur = qty_for_projection * unit_now / eurusd_used
                    value_end_eur = qty_for_projection * unit_end / eurusd_used
                else:
                    value_now_eur = np.nan
                    value_end_eur = np.nan

                vk1, vk2, vk3, vk4 = st.columns(4)
                vk1.metric(
                    f"Current Unit ({asset_ccy})",
                    f"{unit_now:,.4f}",
                    help="Latest mapped market unit price.",
                )
                vk2.metric(
                    f"Projected Unit in {af_horizon}d ({asset_ccy})",
                    f"{unit_end:,.4f}",
                    delta=f"{((unit_end / unit_now) - 1.0) * 100:,.2f}%" if abs(unit_now) > 1e-12 else None,
                    help="Forecasted market unit price at horizon.",
                )
                vk3.metric(
                    "Current Qty Used",
                    f"{qty_for_projection:,.4f}",
                    help="Projection assumes current quantity remains constant (no future buys/sells).",
                )
                vk4.metric(
                    f"Projected Position Value in {af_horizon}d",
                    "n/a" if pd.isna(value_end_eur) else fmt_eur_short(value_end_eur),
                    delta=None if pd.isna(value_end_eur) or pd.isna(value_now_eur) else fmt_eur_short(value_end_eur - value_now_eur),
                    help="Projected current-position value in EUR from unit-price forecast. For USD assets, FX is held flat at latest EURUSD.",
                )

                position_hist = price_hist[["date", "unit_ccy"]].copy()
                if asset_ccy == "EUR":
                    position_hist["position_value_eur"] = qty_for_projection * position_hist["unit_ccy"]
                elif asset_ccy == "USD" and not eurusd.empty:
                    fx_hist = eurusd[["date", "eurusd"]].copy().sort_values("date")
                    position_hist = position_hist.merge(fx_hist, on="date", how="left")
                    position_hist["eurusd"] = position_hist["eurusd"].ffill().bfill()
                    position_hist["position_value_eur"] = qty_for_projection * position_hist["unit_ccy"] / position_hist["eurusd"]
                else:
                    position_hist["position_value_eur"] = np.nan

                forecast_value = forecast_df.copy()
                if asset_ccy == "EUR":
                    forecast_value["position_value_eur"] = qty_for_projection * forecast_value["forecast"]
                elif asset_ccy == "USD" and pd.notna(eurusd_used):
                    forecast_value["position_value_eur"] = qty_for_projection * forecast_value["forecast"] / eurusd_used
                else:
                    forecast_value["position_value_eur"] = np.nan

                fig_pos = go.Figure()
                fig_pos.add_trace(
                    go.Scatter(
                        x=position_hist["date"],
                        y=position_hist["position_value_eur"],
                        mode="lines",
                        name="current-qty value history (EUR)",
                    )
                )
                fig_pos.add_trace(
                    go.Scatter(
                        x=forecast_value["date"],
                        y=forecast_value["position_value_eur"],
                        mode="lines",
                        name="current-qty value forecast (EUR)",
                    )
                )
                fig_pos.update_layout(xaxis_title="Date", yaxis_title="EUR")
                st.plotly_chart(fig_pos, use_container_width=True)
                if asset_ccy == "USD":
                    st.caption(
                        "USD asset projection converts to EUR using latest EURUSD held constant; "
                        "this forecasts market price, not future deposits/trades."
                    )

st.subheader("Trade Execution Scatter")
trade_points = asset_tx[asset_tx["Asset Price"].notna()].copy()
if not trade_points.empty:
    fig_sc = px.scatter(
        trade_points,
        x="date",
        y="Asset Price",
        color="Transfer Type",
        size=trade_points["Asset Quantity"].fillna(0.0).abs().clip(lower=0.01),
        hover_data=["Transaction Type", "Transaction Amount"],
    )
    st.plotly_chart(fig_sc, use_container_width=True)
else:
    st.info("No priced trade points for this asset.")

st.subheader("Asset Ledger")
st.dataframe(
    asset_tx.sort_values("Transaction Time (CET)", ascending=False),
    use_container_width=True,
    hide_index=True,
)
