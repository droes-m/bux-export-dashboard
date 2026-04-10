from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DashboardMetrics:
    portfolio_value_eur: float
    net_deposits_eur: float
    net_external_flows_eur: float
    gain_eur: float
    gain_after_all_cashflows_eur: float
    gain_ex_fees_taxes_eur: float
    gain_pct: float
    cash_balance_eur: float
    market_value_eur: float
    realized_pnl_eur: float
    fees_eur: float
    taxes_eur: float
    dividends_net_eur: float
    interest_eur: float


def build_monthly_performance_view(portfolio_ts: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    if portfolio_ts.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "month_label",
                "portfolio_change_eur",
                "external_flow_eur",
                "market_result_eur",
            ]
        )

    monthly = portfolio_ts.copy()
    monthly["month"] = monthly["date"].dt.to_period("M")
    monthly = (
        monthly.groupby("month", as_index=False)[
            ["portfolio_value_eur", "net_external_flows_eur", "gain_eur"]
        ]
        .last()
        .sort_values("month")
    )
    monthly["portfolio_change_eur"] = monthly["portfolio_value_eur"].diff().fillna(monthly["portfolio_value_eur"])
    monthly["external_flow_eur"] = (
        monthly["net_external_flows_eur"].diff().fillna(monthly["net_external_flows_eur"])
    )
    monthly["market_result_eur"] = monthly["gain_eur"].diff().fillna(monthly["gain_eur"])
    monthly["month_label"] = monthly["month"].dt.strftime("%b %Y")
    if months > 0:
        monthly = monthly.tail(months)
    return monthly.reset_index(drop=True)


def build_holdings_daily(transactions: pd.DataFrame, date_index: pd.DatetimeIndex) -> pd.DataFrame:
    trades = transactions[transactions["signed_quantity"].ne(0) & transactions["Asset Id"].notna()].copy()
    if trades.empty:
        return pd.DataFrame(index=date_index)

    daily_delta = trades.pivot_table(
        index="date",
        columns="Asset Id",
        values="signed_quantity",
        aggfunc="sum",
        fill_value=0.0,
    )
    daily_delta = daily_delta.reindex(date_index, fill_value=0.0)
    holdings = daily_delta.cumsum()
    return holdings


def build_cash_daily(transactions: pd.DataFrame, date_index: pd.DatetimeIndex) -> pd.Series:
    cash = transactions[["date", "Cash Balance Amount"]].dropna(subset=["Cash Balance Amount"]).copy()
    if cash.empty:
        return pd.Series(0.0, index=date_index, name="cash_balance_eur")

    cash = cash.groupby("date", as_index=True)["Cash Balance Amount"].last()
    cash = cash.reindex(date_index).ffill().fillna(0.0)
    cash.name = "cash_balance_eur"
    return cash


def build_external_flows_daily(transactions: pd.DataFrame, date_index: pd.DatetimeIndex) -> pd.Series:
    flows = transactions[transactions["Transaction Category"].eq("deposits")].copy()
    if flows.empty:
        return pd.Series(0.0, index=date_index, name="net_external_flows_eur")

    daily = flows.groupby("date", as_index=True)["Transaction Amount"].sum()
    cumulative = daily.reindex(date_index, fill_value=0.0).cumsum()
    cumulative.name = "net_external_flows_eur"
    return cumulative


def build_market_value_daily(
    holdings_daily: pd.DataFrame,
    mapping_df: pd.DataFrame,
    prices_long: pd.DataFrame,
    eurusd: pd.DataFrame,
) -> tuple[pd.Series, pd.DataFrame]:
    if holdings_daily.empty:
        empty = pd.Series(0.0, index=holdings_daily.index, name="market_value_eur")
        return empty, pd.DataFrame(index=holdings_daily.index)

    ticker_map = mapping_df.set_index("asset_id")["ticker"].to_dict()
    currency_map = mapping_df.set_index("asset_id")["asset_currency"].to_dict()
    scale_map = pd.to_numeric(mapping_df.set_index("asset_id")["price_scale"], errors="coerce").fillna(1.0).to_dict()

    if prices_long.empty:
        empty = pd.Series(0.0, index=holdings_daily.index, name="market_value_eur")
        return empty, pd.DataFrame(index=holdings_daily.index)

    prices = prices_long.pivot_table(index="date", columns="ticker", values="close", aggfunc="last")
    prices = prices.reindex(holdings_daily.index).ffill()

    eurusd_series = eurusd.set_index("date")["eurusd"] if not eurusd.empty else pd.Series(index=holdings_daily.index, dtype=float)
    eurusd_series = eurusd_series.reindex(holdings_daily.index).ffill().bfill()

    per_asset_value = pd.DataFrame(index=holdings_daily.index)

    for asset_id in holdings_daily.columns:
        ticker = ticker_map.get(asset_id, "")
        if not ticker or ticker not in prices.columns:
            continue

        asset_qty = holdings_daily[asset_id]
        price = prices[ticker]
        scale = float(scale_map.get(asset_id, 1.0))
        price = price * scale
        value = asset_qty * price
        asset_ccy = currency_map.get(asset_id, "")

        if asset_ccy == "USD":
            value = value / eurusd_series

        per_asset_value[asset_id] = value

    if per_asset_value.empty:
        mv = pd.Series(0.0, index=holdings_daily.index, name="market_value_eur")
    else:
        mv = per_asset_value.sum(axis=1).rename("market_value_eur")

    return mv, per_asset_value


def build_portfolio_timeseries(
    transactions: pd.DataFrame,
    mapping_df: pd.DataFrame,
    prices_long: pd.DataFrame,
    eurusd: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    start = transactions["date"].min()
    end = max(transactions["date"].max(), pd.Timestamp.today().floor("D"))
    date_index = pd.date_range(start=start, end=end, freq="D")

    holdings_daily = build_holdings_daily(transactions, date_index)
    cash_daily = build_cash_daily(transactions, date_index)
    external_flows_daily = build_external_flows_daily(transactions, date_index)
    market_daily, per_asset_value = build_market_value_daily(holdings_daily, mapping_df, prices_long, eurusd)

    portfolio = pd.concat([cash_daily, external_flows_daily, market_daily], axis=1).fillna(0.0)
    portfolio["portfolio_value_eur"] = portfolio["cash_balance_eur"] + portfolio["market_value_eur"]
    portfolio["net_deposits_eur"] = portfolio["net_external_flows_eur"]
    portfolio["gain_eur"] = portfolio["portfolio_value_eur"] - portfolio["net_external_flows_eur"]
    portfolio["gain_pct"] = portfolio["gain_eur"] / portfolio["net_external_flows_eur"].replace(0, pd.NA)

    return portfolio.reset_index(names="date"), holdings_daily.reset_index(names="date"), per_asset_value.reset_index(names="date")


def compute_metrics(transactions: pd.DataFrame, portfolio_ts: pd.DataFrame) -> DashboardMetrics:
    latest = portfolio_ts.iloc[-1]
    realized = transactions.loc[transactions["Transaction Type"].eq("Sell Trade"), "Profit And Loss Amount"].fillna(0.0).sum()
    fees = transactions.loc[transactions["Transaction Category"].eq("fees"), "Transaction Amount"].fillna(0.0).sum()
    taxes = transactions.loc[transactions["Transaction Category"].eq("tax"), "Transaction Amount"].fillna(0.0).sum()
    div_net = transactions["Dividend Net Amount"].fillna(0.0).sum()
    interest = transactions.loc[transactions["Transaction Category"].eq("interest"), "Transaction Amount"].fillna(0.0).sum()
    net_external = float(latest["net_external_flows_eur"])
    gain_after_all_cashflows = float(latest["portfolio_value_eur"] - net_external)
    gain_ex_fees_taxes = float(gain_after_all_cashflows - fees - taxes)

    gain_pct = float(latest["gain_pct"]) if pd.notna(latest["gain_pct"]) else 0.0

    return DashboardMetrics(
        portfolio_value_eur=float(latest["portfolio_value_eur"]),
        net_deposits_eur=float(latest["net_deposits_eur"]),
        net_external_flows_eur=net_external,
        gain_eur=gain_after_all_cashflows,
        gain_after_all_cashflows_eur=gain_after_all_cashflows,
        gain_ex_fees_taxes_eur=gain_ex_fees_taxes,
        gain_pct=gain_pct,
        cash_balance_eur=float(latest["cash_balance_eur"]),
        market_value_eur=float(latest["market_value_eur"]),
        realized_pnl_eur=float(realized),
        fees_eur=float(fees),
        taxes_eur=float(taxes),
        dividends_net_eur=float(div_net),
        interest_eur=float(interest),
    )
