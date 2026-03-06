from __future__ import annotations

from datetime import date

import pandas as pd
from yahooquery import Ticker as YQTicker
from yahooquery import search as yq_search
import yfinance as yf


def _normalize_download(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=["date", "ticker", "close"])

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        close = data[["Close"]].rename(columns={"Close": tickers[0]})

    long_df = (
        close.reset_index()
        .rename(columns={"Date": "date"})
        .melt(id_vars=["date"], var_name="ticker", value_name="close")
        .dropna(subset=["close"])
    )
    long_df["date"] = pd.to_datetime(long_df["date"]).dt.floor("D")
    return long_df


def _fetch_single_yahooquery(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    try:
        hist = YQTicker(ticker).history(start=start_date, end=end_date, interval="1d")
    except Exception:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    if hist is None or len(hist) == 0:
        return pd.DataFrame(columns=["date", "ticker", "close"])

    df = hist.reset_index()
    if "date" not in df.columns:
        return pd.DataFrame(columns=["date", "ticker", "close"])

    if "adjclose" in df.columns:
        close_col = "adjclose"
    elif "close" in df.columns:
        close_col = "close"
    else:
        return pd.DataFrame(columns=["date", "ticker", "close"])

    out = df[["date", close_col]].rename(columns={close_col: "close"})
    out = out.dropna(subset=["close"])
    if out.empty:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    out["date"] = pd.to_datetime(out["date"]).dt.floor("D")
    out["ticker"] = ticker
    out = out.sort_values("date").reset_index(drop=True)
    return out


def _fetch_single_stooq(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    # Kept function name for compatibility: currently uses yahooquery fallback instead of pandas-datareader.
    return _fetch_single_yahooquery(ticker, start_date, end_date)


def fetch_prices(tickers: list[str], start_date: date, end_date: date) -> pd.DataFrame:
    tickers = sorted(set(t for t in tickers if isinstance(t, str) and t.strip()))
    if not tickers:
        return pd.DataFrame(columns=["date", "ticker", "close"])

    yf_prices = pd.DataFrame(columns=["date", "ticker", "close"])
    try:
        raw = yf.download(
            tickers=tickers,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False,
            interval="1d",
            group_by="column",
        )
        yf_prices = _normalize_download(raw, tickers)
    except Exception:
        pass

    found = set(yf_prices["ticker"].unique()) if not yf_prices.empty else set()
    missing = [t for t in tickers if t not in found]

    stooq_parts = []
    for t in missing:
        stooq_px = _fetch_single_stooq(t, start_date, end_date)
        if not stooq_px.empty:
            stooq_parts.append(stooq_px)

    if stooq_parts:
        stooq_df = pd.concat(stooq_parts, ignore_index=True)
        all_px = pd.concat([yf_prices, stooq_df], ignore_index=True)
    else:
        all_px = yf_prices

    if all_px.empty:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    return all_px.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="last").reset_index(drop=True)


def fetch_eurusd(start_date: date, end_date: date) -> pd.DataFrame:
    fx = fetch_prices(["EURUSD=X"], start_date, end_date)
    fx = fx.rename(columns={"close": "eurusd"}).drop(columns=["ticker"])
    return fx


def suggest_tickers_by_price_match(
    asset_name: str,
    target_price: float,
    buy_date: date,
    max_results: int = 5,
) -> pd.DataFrame:
    quotes: list[dict] = []
    try:
        yq = yq_search(asset_name)
        yq_quotes = yq.get("quotes", []) if isinstance(yq, dict) else []
        quotes.extend(
            {
                "symbol": q.get("symbol", ""),
                "shortname": q.get("shortname", q.get("longname", "")),
                "exchange": q.get("exchDisp", q.get("exchange", "")),
            }
            for q in yq_quotes
        )
    except Exception:
        pass

    try:
        search = yf.Search(asset_name, max_results=20)
        yf_quotes = getattr(search, "quotes", []) or []
        quotes.extend(yf_quotes)
    except Exception:
        pass

    if not quotes:
        return pd.DataFrame(columns=["ticker", "shortname", "exchange", "match_price", "relative_error"])

    seen = set()
    dedup_quotes = []
    for q in quotes:
        symbol = str(q.get("symbol", "")).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        dedup_quotes.append(q)

    rows: list[dict] = []
    for quote in dedup_quotes:
        ticker = quote.get("symbol")
        if not ticker:
            continue

        hist = fetch_prices([ticker], buy_date, buy_date + pd.Timedelta(days=5))
        if hist.empty:
            continue

        match_price = float(hist["close"].iloc[0])
        rel_error = abs(match_price - target_price) / max(abs(target_price), 1e-9)
        rows.append(
            {
                "ticker": ticker,
                "shortname": quote.get("shortname", ""),
                "exchange": quote.get("exchange", ""),
                "match_price": match_price,
                "relative_error": rel_error,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["ticker", "shortname", "exchange", "match_price", "relative_error"])

    out = pd.DataFrame(rows).sort_values("relative_error").head(max_results).reset_index(drop=True)
    return out


def _to_records_df(obj) -> pd.DataFrame:
    try:
        if obj is None:
            return pd.DataFrame()
        if isinstance(obj, pd.DataFrame):
            return obj.copy()
        return pd.DataFrame(obj)
    except Exception:
        return pd.DataFrame()


def fetch_security_overview(ticker: str) -> dict:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "Missing ticker.", "kind": "unknown"}

    try:
        yt = yf.Ticker(ticker)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "kind": "unknown"}

    info = {}
    fast_info = {}
    try:
        info = yt.info or {}
    except Exception:
        info = {}
    try:
        fast_info = dict(getattr(yt, "fast_info", {}) or {})
    except Exception:
        fast_info = {}

    quote_type = str(info.get("quoteType", "") or "").upper()
    if not quote_type:
        quote_type = str(info.get("typeDisp", "") or "").upper()
    is_etf = (
        quote_type == "ETF"
        or bool(str(info.get("fundFamily", "")).strip())
        or bool(info.get("annualReportExpenseRatio"))
    )
    kind = "etf" if is_etf else "stock"

    summary = {
        "ticker": ticker,
        "kind": kind,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "quote_type": quote_type or ("ETF" if is_etf else "EQUITY"),
        "currency": info.get("currency") or fast_info.get("currency"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "country": info.get("country"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap") or fast_info.get("market_cap"),
        "pe_trailing": info.get("trailingPE"),
        "pe_forward": info.get("forwardPE"),
        "eps_trailing": info.get("trailingEps"),
        "revenue_growth": info.get("revenueGrowth"),
        "operating_margin": info.get("operatingMargins"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow") or fast_info.get("year_low"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh") or fast_info.get("year_high"),
        "expense_ratio": info.get("annualReportExpenseRatio") or info.get("expenseRatio"),
        "total_assets": info.get("totalAssets"),
        "fund_family": info.get("fundFamily"),
        "category": info.get("category"),
        "yield": info.get("yield"),
        "three_year_avg_return": info.get("threeYearAverageReturn"),
        "five_year_avg_return": info.get("fiveYearAverageReturn"),
        "summary_text": info.get("longBusinessSummary") or info.get("longName"),
    }

    holdings_df = pd.DataFrame()
    try:
        fd = getattr(yt, "funds_data", None)
        if fd is not None:
            holdings_df = _to_records_df(getattr(fd, "top_holdings", None))
    except Exception:
        holdings_df = pd.DataFrame()

    if holdings_df.empty:
        try:
            yq = YQTicker(ticker)
            qsum = yq.fund_holding_info
            if isinstance(qsum, dict):
                item = qsum.get(ticker) if ticker in qsum else next(iter(qsum.values()), {})
                if isinstance(item, dict):
                    maybe = item.get("holdings", [])
                    holdings_df = _to_records_df(maybe)
        except Exception:
            holdings_df = pd.DataFrame()

    if not holdings_df.empty:
        cols = [c for c in holdings_df.columns if str(c).lower() in {"symbol", "name", "holdingname", "holding", "weight", "holdingpercent"}]
        if cols:
            holdings_df = holdings_df[cols].copy()

    return {
        "ok": True,
        "kind": kind,
        "summary": summary,
        "top_holdings": holdings_df.reset_index(drop=True),
    }
