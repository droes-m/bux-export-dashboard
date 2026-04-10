from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.analytics import build_portfolio_timeseries, compute_metrics
from src.data import build_security_master, load_transactions
from src.mapping import load_or_init_security_map, save_security_map
from src.market import fetch_eurusd, fetch_prices, fetch_security_overview, suggest_tickers_by_price_match

DEFAULT_CSV = ""
MAP_PATH = Path("data/security_map.csv")

DEFAULT_NAME_TO_TICKER = {
    "Alphabet A": ("GOOGL", "NASDAQ", "seed_default", "medium"),
    "Apple": ("AAPL", "NASDAQ", "seed_default", "high"),
    "Duolingo": ("DUOL", "NASDAQ", "seed_default", "high"),
    "Enphase Energy": ("ENPH", "NASDAQ", "seed_default", "high"),
    "NVIDIA": ("NVDA", "NASDAQ", "seed_default", "high"),
    "Qualcomm": ("QCOM", "NASDAQ", "seed_default", "high"),
    "Tesla": ("TSLA", "NASDAQ", "seed_default", "high"),
    "Vanguard S&P 500": ("VUSA.AS", "Euronext Amsterdam", "seed_default", "medium"),
    "iShares Global Clean Energy": ("IQQH.DE", "XETRA", "seed_default", "medium"),
    "iShares Automation & Robotics": ("2B76.DE", "XETRA", "seed_default", "medium"),
}

DEFAULT_ISIN_TO_TICKER = {
    "BE0974313455": ("ECONB.BR", "Brussels", "seed_isin", "high", 1.0),
    "IE00BJXRZJ40": ("CYBP.L", "London", "seed_isin", "medium", 1.0),
    "IE00B8GKDB10": ("VHYL.AS", "Amsterdam", "seed_isin", "high", 1.0),
    "IE00B1XNHC34": ("IQQH.DE", "XETRA", "seed_isin", "medium", 1.0),
    "IE000I8KRLL9": ("SEC0.DE", "XETRA", "seed_isin", "high", 1.0),
    "IE00BQN1K786": ("CEMR.DE", "XETRA", "seed_isin", "medium", 1.0),
}

EUR_TICKER_SUFFIXES = (".DE", ".AS", ".PA", ".BR")


def fmt_eur_short(value: float) -> str:
    sign = "-" if value < 0 else ""
    abs_v = abs(value)
    if abs_v >= 1_000_000:
        return f"{sign}EUR {abs_v / 1_000_000:.2f}M"
    if abs_v >= 1_000:
        return f"{sign}EUR {abs_v / 1_000:.2f}k"
    return f"{sign}EUR {abs_v:,.2f}"


def mapped_holdings_coverage(holdings_ts: pd.DataFrame, mapped_df: pd.DataFrame) -> float:
    if holdings_ts.empty:
        return 1.0
    latest = holdings_ts.iloc[-1].drop(labels=["date"])
    latest = latest[latest.abs() > 1e-9]
    if latest.empty:
        return 1.0
    mapped_asset_ids = set(mapped_df.loc[mapped_df["ticker"].astype(str).str.strip().ne(""), "asset_id"].tolist())
    mapped_count = sum(1 for asset_id in latest.index if asset_id in mapped_asset_ids)
    return mapped_count / len(latest)


def autofill_mapping_defaults(mapping_df: pd.DataFrame) -> pd.DataFrame:
    out = mapping_df.copy()
    for i, row in out.iterrows():
        if str(row.get("ticker", "")).strip():
            continue
        asset_id = row.get("asset_id", "")
        if asset_id in DEFAULT_ISIN_TO_TICKER:
            ticker, exchange, source, confidence, scale = DEFAULT_ISIN_TO_TICKER[asset_id]
            out.at[i, "ticker"] = ticker
            out.at[i, "price_scale"] = scale
            out.at[i, "exchange"] = exchange
            out.at[i, "source"] = source
            out.at[i, "confidence"] = confidence
            continue
        asset_name = row.get("asset_name", "")
        if asset_name in DEFAULT_NAME_TO_TICKER:
            ticker, exchange, source, confidence = DEFAULT_NAME_TO_TICKER[asset_name]
            out.at[i, "ticker"] = ticker
            out.at[i, "price_scale"] = 1.0
            out.at[i, "exchange"] = exchange
            out.at[i, "source"] = source
            out.at[i, "confidence"] = confidence

    # Fallback: infer missing asset currency from common EUR listing suffixes.
    for i, row in out.iterrows():
        ccy = str(row.get("asset_currency", "")).strip().upper()
        if ccy:
            continue
        ticker = str(row.get("ticker", "")).strip().upper()
        if ticker.endswith(EUR_TICKER_SUFFIXES):
            out.at[i, "asset_currency"] = "EUR"
            if str(row.get("source", "")).strip() in ("", "pending"):
                out.at[i, "source"] = "ticker_suffix_infer"
            if str(row.get("confidence", "")).strip() in ("", "unmapped"):
                out.at[i, "confidence"] = "low"
            notes = str(row.get("notes", "")).strip()
            if "currency inferred from ticker suffix" not in notes.lower():
                extra = "currency inferred from ticker suffix"
                out.at[i, "notes"] = f"{notes}; {extra}".strip("; ").strip()
    return out


def compute_asset_valuation_anomalies(
    tx: pd.DataFrame, mapped: pd.DataFrame, holdings_ts: pd.DataFrame, asset_value_ts: pd.DataFrame
) -> pd.DataFrame:
    if asset_value_ts.empty:
        return pd.DataFrame(
            columns=["asset_id", "asset_name", "ticker", "current_scale", "suggested_scale", "issue", "details"]
        )

    out: list[dict] = []
    values = asset_value_ts.set_index("date")
    holdings = holdings_ts.set_index("date") if not holdings_ts.empty else pd.DataFrame(index=values.index)
    for _, row in mapped.iterrows():
        asset_id = row["asset_id"]
        if asset_id not in values.columns:
            continue
        series = values[asset_id].dropna()
        if len(series) < 5:
            continue

        buys = tx[(tx["Asset Id"].eq(asset_id)) & tx["Transfer Type"].eq("ASSET_TRADE_BUY") & tx["Asset Price"].notna()]
        if buys.empty:
            continue
        med_buy = float(buys["Asset Price"].median())
        if med_buy <= 0:
            continue

        if asset_id not in holdings.columns:
            continue
        qty = holdings[asset_id].replace(0, pd.NA)
        unit_price = (values[asset_id] / qty).dropna()
        if unit_price.empty:
            continue
        unit_pct = unit_price.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        max_jump = float(unit_pct.abs().max()) if not unit_pct.empty else 0.0
        current_scale = float(row.get("price_scale", 1.0) or 1.0)
        if max_jump > 0.3:
            out.append(
                {
                    "asset_id": asset_id,
                    "asset_name": row.get("asset_name", ""),
                    "ticker": row.get("ticker", ""),
                    "current_scale": current_scale,
                    "suggested_scale": current_scale,
                    "issue": "Large daily price jump",
                    "details": f"Max abs unit-price day move {max_jump:.0%}.",
                }
            )
        ratio = float(unit_price.median() / med_buy)
        candidates = [current_scale * x for x in (0.01, 0.1, 1.0, 10.0, 100.0)]
        suggested_scale = min(candidates, key=lambda s: abs(np.log10(max(ratio * (s / current_scale), 1e-9))))
        if ratio > 20 or ratio < 0.05:
            out.append(
                {
                    "asset_id": asset_id,
                    "asset_name": row.get("asset_name", ""),
                    "ticker": row.get("ticker", ""),
                    "current_scale": current_scale,
                    "suggested_scale": suggested_scale,
                    "issue": "Potential quote-scale mismatch",
                    "details": f"Median implied price is {ratio:.1f}x buy baseline. Check ticker/price_scale.",
                }
            )
        asset_ccy = str(row.get("asset_currency", "")).upper()
        ticker = str(row.get("ticker", "")).upper()
        if asset_ccy == "EUR" and ticker.endswith(".L"):
            out.append(
                {
                    "asset_id": asset_id,
                    "asset_name": row.get("asset_name", ""),
                    "ticker": row.get("ticker", ""),
                    "current_scale": current_scale,
                    "suggested_scale": current_scale,
                    "issue": "Listing-currency mismatch risk",
                    "details": "EUR asset mapped to London ticker (.L). Prefer EUR listing (.DE/.AS/.PA).",
                }
            )

    if not out:
        return pd.DataFrame(
            columns=["asset_id", "asset_name", "ticker", "current_scale", "suggested_scale", "issue", "details"]
        )
    return pd.DataFrame(out).drop_duplicates()


@st.cache_data(show_spinner=False)
def load_transactions_cached(path_or_bytes: str | bytes) -> pd.DataFrame:
    if isinstance(path_or_bytes, bytes):
        from io import BytesIO

        return load_transactions(BytesIO(path_or_bytes))
    return load_transactions(path_or_bytes)


@st.cache_data(show_spinner=False)
def fetch_market_data_cached(tickers: tuple[str, ...], start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    start_dt = pd.Timestamp(start).date() - timedelta(days=5)
    end_dt = pd.Timestamp(end).date() + timedelta(days=2)
    prices = fetch_prices(list(tickers), start_dt, end_dt)
    eurusd = fetch_eurusd(start_dt, end_dt)
    return prices, eurusd


def render_data_source_sidebar(current_page: str = "Home") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    with st.sidebar:
        st.header("Data Source")
        csv_path = st.text_input("CSV path", value=DEFAULT_CSV, key="csv_path")
        upload = st.file_uploader("or upload CSV", type=["csv"], key="csv_upload")

    if upload is not None:
        tx = load_transactions_cached(upload.getvalue())
        source_label = upload.name
    elif csv_path.strip():
        tx = load_transactions_cached(csv_path)
        source_label = csv_path
    else:
        st.info("Upload a BUX export CSV or provide a local CSV path in the sidebar.")
        st.stop()

    master = build_security_master(tx)
    security_map = load_or_init_security_map(master, MAP_PATH)
    return tx, master, security_map, source_label


def build_portfolio_bundle(tx: pd.DataFrame, mapped: pd.DataFrame) -> dict:
    effective_mapping = autofill_mapping_defaults(mapped.copy())
    mapped_tickers = tuple(
        sorted(set(effective_mapping.loc[effective_mapping["ticker"].astype(str).str.strip().ne(""), "ticker"].tolist()))
    )

    start = tx["date"].min().date().isoformat()
    end = max(tx["date"].max(), pd.Timestamp.today().floor("D")).date().isoformat()

    if mapped_tickers:
        prices_long, eurusd = fetch_market_data_cached(mapped_tickers, start, end)
    else:
        prices_long = pd.DataFrame(columns=["date", "ticker", "close"])
        eurusd = pd.DataFrame(columns=["date", "eurusd"])

    portfolio_ts, holdings_ts, asset_value_ts = build_portfolio_timeseries(tx, effective_mapping, prices_long, eurusd)
    metrics = compute_metrics(tx, portfolio_ts)
    coverage = mapped_holdings_coverage(holdings_ts, effective_mapping)
    anomalies = compute_asset_valuation_anomalies(tx, effective_mapping, holdings_ts, asset_value_ts)

    return {
        "mapped_tickers": mapped_tickers,
        "prices_long": prices_long,
        "eurusd": eurusd,
        "portfolio_ts": portfolio_ts,
        "holdings_ts": holdings_ts,
        "asset_value_ts": asset_value_ts,
        "metrics": metrics,
        "coverage": coverage,
        "anomalies": anomalies,
        "effective_mapping": effective_mapping,
    }


def save_mapping(mapping_df: pd.DataFrame) -> None:
    save_security_map(mapping_df, MAP_PATH)


def suggest_candidates(asset_name: str, target_price: float, target_date) -> pd.DataFrame:
    return suggest_tickers_by_price_match(asset_name, target_price, target_date)


@st.cache_data(show_spinner=False)
def fetch_security_overview_cached(ticker: str) -> dict:
    return fetch_security_overview(ticker)
