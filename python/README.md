# BUX Portfolio Dashboard

Streamlit dashboard for BUX transaction exports with:

- Multi-page architecture
- Portfolio overview (performance, drawdown, allocation, rolling return)
- Asset drilldown (per-asset quantity/value/trade diagnostics)
- Cashflow and costs analytics
- Forecast and regression extrapolation
- Mapping and valuation QA workflows
- Advanced transactions explorer + export

## Run

```bash
uv sync
UV_CACHE_DIR=/tmp/uv-cache uv run streamlit run app.py
```

Open the local Streamlit URL shown in the terminal.

## Data inputs

- Upload a BUX export CSV in the sidebar, or paste a local CSV path there.
- No sample transaction exports are included in this repository.

## Asset mapping

Market data needs ticker symbols. The app keeps mappings in:

- `data/security_map.csv`

This file is generated locally and is ignored by git by default.

Workflow:

1. Open **Asset Mapping (ISIN -> ticker)** in the app.
2. Click **Auto-fill known tickers** (uses ISIN-first defaults).
3. Fill remaining `ticker` values for each `asset_id` (ISIN).
4. Set `price_scale` when quote units differ from instrument units (example: `0.01` for GBp quotes).
5. Click **Save mapping**.
6. App fetches daily prices (yfinance + yahooquery fallback) and updates valuation/gains.
7. If ticker is unknown, use the built-in **price-match ticker suggestion** helper, then apply a candidate directly.

## Pages

- Home: quick portfolio health summary and navigation
- Overview: complete portfolio-level analytics
- Asset Drilldown: per-instrument diagnostics
- Cashflows & Costs: contribution/income/cost decomposition
- Forecast & Regression: trend projection with uncertainty band
- Mapping & QA: mapping editor, anomaly detection, price-scale fixes
- Transactions Explorer: full ledger filtering and CSV export

For hard ETFs, map manually with exchange suffixes when needed (for example `.AS`, `.PA`, `.DE`).

## How gains are computed

- `portfolio_value_eur = cash_balance_eur + market_value_eur`
- `net_deposits_eur = cumulative Sepa Deposit amounts`
- `gain_eur = portfolio_value_eur - net_deposits_eur`

Notes:

- USD assets are converted to EUR using `EURUSD=X`.
- Unmapped assets are excluded from market value until mapped.
- The app raises valuation-anomaly warnings and can suggest `price_scale` corrections.
