from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard_data import build_portfolio_bundle, fmt_eur_short, render_data_source_sidebar

st.set_page_config(page_title="Forecast & Regression", layout="wide")
st.title("Forecast & Regression")
st.caption("Trend extrapolation on historical daily series. Use as directional context, not investment advice.")

tx, _master, security_map, source_label = render_data_source_sidebar(current_page="Forecast And Regression")
bundle = build_portfolio_bundle(tx, security_map)
portfolio_ts = bundle["portfolio_ts"].copy()
prices_long = bundle["prices_long"].copy()
effective_mapping = bundle["effective_mapping"].copy()

st.caption(f"Loaded {len(tx)} transactions from `{source_label}`")

series_map = {
    "Portfolio Value": "portfolio_value_eur",
    "Gain": "gain_eur",
    "Market Value": "market_value_eur",
}

c1, c2, c3 = st.columns(3)
with c1:
    series_label = st.selectbox("Target series", list(series_map.keys()))
with c2:
    lookback_days = st.slider("Lookback window (days)", min_value=90, max_value=2000, value=600, step=30)
with c3:
    horizon_days = st.slider("Forecast horizon (days)", min_value=30, max_value=3650, value=365, step=30)

method = st.selectbox("Forecast method", ["Auto", "Linear", "Quadratic", "Exponential", "CAGR", "Flat"])

col = series_map[series_label]
base = portfolio_ts[["date", col]].dropna().copy().sort_values("date")
if len(base) < 30:
    st.warning("Not enough points for forecasting.")
    st.stop()

cutoff = base["date"].max() - pd.Timedelta(days=lookback_days)
fit_df = base[base["date"] >= cutoff].copy()
if len(fit_df) < 20:
    fit_df = base.tail(120).copy()

fit_df["x"] = (fit_df["date"] - fit_df["date"].min()).dt.days.astype(float)
x = fit_df["x"].to_numpy()
y = fit_df[col].astype(float).to_numpy()


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

if method == "Auto":
    chosen = min(candidates.values(), key=lambda m: m["rmse"])
else:
    if method not in candidates:
        st.warning(f"Method `{method}` is not valid for this series window. Falling back to Linear.")
        chosen = candidates["Linear"]
    else:
        chosen = candidates[method]

last_date = fit_df["date"].max()
future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
future_x = (future_dates - fit_df["date"].min()).days.astype(float)


def predict(model: dict, xv: np.ndarray) -> np.ndarray:
    name = model["name"]
    coef = model["coef"]
    if name == "Linear":
        return np.polyval(coef, xv)
    if name == "Quadratic":
        return np.polyval(coef, xv)
    if name == "Exponential":
        return np.exp(np.polyval(coef, xv))
    if name == "CAGR":
        g, start_val, x0 = coef
        return start_val * ((1.0 + g) ** (xv - x0))
    return np.full_like(xv, float(coef[0]), dtype=float)


fit_line = chosen["fit"]
future_pred = predict(chosen, future_x)
resid = y - fit_line
resid_std = float(np.std(resid))

forecast_df = pd.DataFrame({"date": future_dates, "forecast": future_pred})
forecast_df["upper"] = forecast_df["forecast"] + 1.0 * resid_std
forecast_df["lower"] = forecast_df["forecast"] - 1.0 * resid_std

k1, k2, k3, k4 = st.columns(4)
k1.metric("Selected Model", chosen["name"], help="Forecast method used for fitted trend and projection.")
k2.metric("R2", f"{chosen['r2']:.3f}", help="Goodness of fit on the lookback sample (higher is better).")
k3.metric("RMSE", fmt_eur_short(chosen["rmse"]), help="Root-mean-square fit error on the lookback sample, in EUR.")
k4.metric("Residual Vol", fmt_eur_short(resid_std), help="Standard deviation of residuals around the fitted model.")

with st.expander("Model comparison", expanded=False):
    comp = pd.DataFrame(
        [{"model": m["name"], "r2": m["r2"], "rmse": m["rmse"]} for m in candidates.values()]
    ).sort_values("rmse")
    st.dataframe(comp, use_container_width=True, hide_index=True)

fig = go.Figure()
fig.add_trace(go.Scatter(x=base["date"], y=base[col], mode="lines", name="history"))
fig.add_trace(go.Scatter(x=fit_df["date"], y=fit_line, mode="lines", name=f"{chosen['name'].lower()} fit"))
fig.add_trace(go.Scatter(x=forecast_df["date"], y=forecast_df["forecast"], mode="lines", name="forecast"))
fig.add_trace(
    go.Scatter(
        x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
        y=pd.concat([forecast_df["upper"], forecast_df["lower"][::-1]]),
        fill="toself",
        line=dict(color="rgba(0,0,0,0)"),
        name="±1σ band",
        opacity=0.2,
    )
)
fig.update_layout(xaxis_title="Date", yaxis_title="EUR")

# Contribution-aware scenario (for Portfolio Value forecasts).
show_contrib = st.checkbox("Include recurring contribution scenario", value=(series_label == "Portfolio Value"))
contrib_forecast = None
contrib_summary = None
if show_contrib:
    if series_label != "Portfolio Value":
        st.info("Contribution scenario currently applies to `Portfolio Value` forecasts.")
    else:
        mapped_assets = (
            effective_mapping[effective_mapping["ticker"].astype(str).str.strip().ne("")][["asset_name", "ticker"]]
            .dropna(subset=["asset_name"])
            .drop_duplicates(subset=["asset_name"])
            .sort_values("asset_name")
        )
        if mapped_assets.empty:
            st.info("No mapped assets available for contribution allocation.")
        else:
            asset_options = mapped_assets["asset_name"].tolist()
            default_sp500 = next((a for a in asset_options if "S&P 500" in a), asset_options[0])
            default_mom = next((a for a in asset_options if "Momentum Factor" in a), asset_options[min(1, len(asset_options) - 1)])

            st.subheader("Contribution Scenario")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                contrib_day = st.slider("Deposit day of month", min_value=1, max_value=28, value=5)
            with c2:
                a1 = st.selectbox("Allocation asset #1", asset_options, index=asset_options.index(default_sp500))
            with c3:
                a2 = st.selectbox("Allocation asset #2", asset_options, index=asset_options.index(default_mom))
            with c4:
                st.caption("Monthly allocation (EUR)")
                amt1 = st.number_input(f"{a1} amount", min_value=0.0, value=200.0, step=10.0, key="alloc_amt_1")
                amt2 = st.number_input(f"{a2} amount", min_value=0.0, value=300.0, step=10.0, key="alloc_amt_2")

            monthly_contrib = float(amt1 + amt2)
            if monthly_contrib <= 0:
                st.info("Monthly contribution is zero; scenario equals baseline forecast.")
            else:
                asset_to_ticker = dict(zip(mapped_assets["asset_name"], mapped_assets["ticker"]))
                alloc = [(a1, float(amt1)), (a2, float(amt2))]
                alloc = [(name, amt) for name, amt in alloc if amt > 0]

                cutoff_dt = fit_df["date"].max() - pd.Timedelta(days=lookback_days)

                def expected_daily_return(asset_name: str) -> float:
                    ticker = asset_to_ticker.get(asset_name, "")
                    if not ticker:
                        return 0.0
                    px = prices_long.loc[prices_long["ticker"].eq(ticker), ["date", "close"]].sort_values("date")
                    if px.empty:
                        return 0.0
                    px = px[px["date"] >= cutoff_dt].copy()
                    if len(px) < 30:
                        return 0.0
                    rets = px["close"].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
                    if rets.empty:
                        return 0.0
                    return float(rets.mean())

                weighted_mu = 0.0
                total_alloc = sum(amt for _, amt in alloc)
                alloc_rows = []
                for name, amt in alloc:
                    mu = expected_daily_return(name)
                    w = amt / total_alloc if total_alloc > 0 else 0.0
                    weighted_mu += w * mu
                    alloc_rows.append({"asset": name, "monthly_eur": amt, "weight": w, "expected_daily_return": mu})

                scenario_values = []
                scenario_contrib_cum = []
                val = float(base[col].iloc[-1])
                contrib_cum = 0.0
                current_month = None
                for d in future_dates:
                    monthly_add = 0.0
                    if (current_month != (d.year, d.month)) and (d.day >= contrib_day):
                        monthly_add = monthly_contrib
                        current_month = (d.year, d.month)
                    val = val * (1.0 + weighted_mu) + monthly_add
                    contrib_cum += monthly_add
                    scenario_values.append(val)
                    scenario_contrib_cum.append(contrib_cum)

                contrib_forecast = pd.DataFrame(
                    {
                        "date": future_dates,
                        "forecast_with_contrib": scenario_values,
                        "contrib_cumulative": scenario_contrib_cum,
                    }
                )
                start_value = float(base[col].iloc[-1])
                end_value = float(contrib_forecast["forecast_with_contrib"].iloc[-1])
                contrib_principal = float(contrib_forecast["contrib_cumulative"].iloc[-1]) if not contrib_forecast.empty else 0.0
                market_gain_total = end_value - start_value - contrib_principal
                # Split market gain into growth on current capital vs growth on future contributions.
                no_contrib_val = start_value
                for _ in future_dates:
                    no_contrib_val = no_contrib_val * (1.0 + weighted_mu)
                market_gain_on_start = no_contrib_val - start_value
                market_gain_on_new_contrib = market_gain_total - market_gain_on_start
                contrib_summary = {
                    "monthly_contrib": monthly_contrib,
                    "weighted_mu": weighted_mu,
                    "alloc_table": pd.DataFrame(alloc_rows),
                    "end_value": end_value,
                    "start_value": start_value,
                    "contrib_principal": contrib_principal,
                    "market_gain_total": market_gain_total,
                    "market_gain_on_start": market_gain_on_start,
                    "market_gain_on_new_contrib": market_gain_on_new_contrib,
                }

                fig.add_trace(
                    go.Scatter(
                        x=contrib_forecast["date"],
                        y=contrib_forecast["forecast_with_contrib"],
                        mode="lines",
                        name="forecast + contributions",
                        line=dict(dash="dot"),
                    )
                )

st.plotly_chart(fig, use_container_width=True)

end_forecast = float(forecast_df["forecast"].iloc[-1])
current_value = float(base[col].iloc[-1])
delta = end_forecast - current_value

c4, c5 = st.columns(2)
with c4:
    st.metric(
        f"Projected {series_label} in {horizon_days}d",
        fmt_eur_short(end_forecast),
        delta=fmt_eur_short(delta),
        help="Model projection at forecast horizon; delta is versus latest observed value.",
    )
with c5:
    linear_slope = float(np.polyfit(x, y, deg=1)[0])
    st.metric("Linear Trend / day", fmt_eur_short(linear_slope), help="Slope of a simple linear fit over the selected lookback.")

if contrib_summary is not None:
    c6, c7, c8 = st.columns(3)
    with c6:
        st.metric(
            "Projected with Contributions",
            fmt_eur_short(contrib_summary["end_value"]),
            delta=fmt_eur_short(contrib_summary["end_value"] - end_forecast),
            help="Same forecast horizon including recurring monthly contributions and weighted expected return.",
        )
    with c7:
        st.metric(
            "Monthly Contribution",
            fmt_eur_short(contrib_summary["monthly_contrib"]),
            help="Total scheduled monthly contribution in scenario.",
        )
    with c8:
        st.metric(
            "Weighted Daily Return Assumption",
            f"{contrib_summary['weighted_mu'] * 100:,.3f}%",
            help="Weighted average daily return inferred from selected allocation assets over the lookback window.",
        )
    d1, d2, d3 = st.columns(3)
    d1.metric(
        "Deposited Principal (horizon)",
        fmt_eur_short(contrib_summary["contrib_principal"]),
        help="Total new cash planned to be deposited over the forecast horizon.",
    )
    d2.metric(
        "Market Gains (scenario total)",
        fmt_eur_short(contrib_summary["market_gain_total"]),
        help="Projected end value minus current value minus deposited principal.",
    )
    d3.metric(
        "Market Gains on New Deposits",
        fmt_eur_short(contrib_summary["market_gain_on_new_contrib"]),
        help="Estimated growth attributable to invested new contributions, beyond their principal.",
    )
    breakdown = pd.DataFrame(
        [
            {"component": "Current portfolio value (start)", "eur": contrib_summary["start_value"]},
            {"component": "Deposited principal (future)", "eur": contrib_summary["contrib_principal"]},
            {"component": "Market gains on start capital", "eur": contrib_summary["market_gain_on_start"]},
            {"component": "Market gains on new deposits", "eur": contrib_summary["market_gain_on_new_contrib"]},
        ]
    )
    st.bar_chart(breakdown.set_index("component"))
    with st.expander("Contribution allocation assumptions", expanded=False):
        st.dataframe(
            contrib_summary["alloc_table"].assign(
                weight=lambda d: d["weight"].map(lambda x: f"{x * 100:.1f}%"),
                expected_daily_return=lambda d: d["expected_daily_return"].map(lambda x: f"{x * 100:.3f}%"),
            ),
            use_container_width=True,
            hide_index=True,
        )

st.subheader("Forecast Table")
show_every = st.selectbox("Sampling", ["Daily", "Weekly", "Monthly", "Quarterly"], index=1)
out = forecast_df.copy()
if contrib_forecast is not None:
    out = out.merge(contrib_forecast, on="date", how="left")
if show_every == "Weekly":
    out = out.iloc[::7, :]
elif show_every == "Monthly":
    out = out.iloc[::30, :]
elif show_every == "Quarterly":
    out = out.iloc[::90, :]
st.dataframe(out, use_container_width=True, hide_index=True)
