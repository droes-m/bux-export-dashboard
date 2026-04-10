from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard_data import (
    MAP_PATH,
    autofill_mapping_defaults,
    build_portfolio_bundle,
    fmt_eur_short,
    mapped_holdings_coverage,
    render_data_source_sidebar,
    save_mapping,
    suggest_candidates,
)

st.set_page_config(page_title="Mapping & QA", layout="wide")
st.title("Mapping & QA")

tx, _master, security_map, source_label = render_data_source_sidebar()
st.caption(f"Loaded {len(tx)} transactions from `{source_label}` | Mapping file: `{MAP_PATH}`")

editable_cols = [
    "asset_id",
    "asset_name",
    "asset_currency",
    "ticker",
    "price_scale",
    "exchange",
    "source",
    "confidence",
    "notes",
]

edited = st.data_editor(
    security_map[editable_cols],
    use_container_width=True,
    num_rows="fixed",
    hide_index=True,
    key="qa_map_editor",
)
edited["price_scale"] = pd.to_numeric(edited["price_scale"], errors="coerce").fillna(1.0)

c1, c2, c3 = st.columns([1, 1, 3])
with c1:
    if st.button("Save mapping", type="primary"):
        save_mapping(edited)
        st.success("Saved mapping")
with c2:
    if st.button("Auto-fill known tickers"):
        edited = autofill_mapping_defaults(edited)
        save_mapping(edited)
        st.success("Applied defaults and saved")
        st.rerun()
with c3:
    unresolved = int((edited["ticker"].astype(str).str.strip() == "").sum())
    st.info(f"Unmapped rows (all assets): {unresolved} / {len(edited)} | use `price_scale=0.01` for GBp quotes")

bundle = build_portfolio_bundle(tx, edited)
metrics = bundle["metrics"]
coverage_effective = bundle["coverage"]
anomalies = bundle["anomalies"]
coverage_strict = mapped_holdings_coverage(bundle["holdings_ts"], edited)
effective_mapping = bundle["effective_mapping"].copy()

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Saved Mapping Coverage (strict)",
    f"{coverage_strict:.0%}",
    help="Share of latest non-zero holdings mapped using only values saved in the editable table.",
)
k2.metric(
    "Effective Coverage (with defaults)",
    f"{coverage_effective:.0%}",
    help="Share of latest non-zero holdings mapped after applying built-in auto-fill defaults at runtime.",
)
k3.metric(
    "Portfolio Value (preview)",
    fmt_eur_short(metrics.portfolio_value_eur),
    help="Preview valuation using the currently edited mapping table.",
)
k4.metric(
    "Gain (preview)",
    fmt_eur_short(metrics.gain_after_all_cashflows_eur),
    help="Preview gain (portfolio value - net external flows) under current mapping edits.",
)

saved_view = edited[["asset_id", "asset_name", "ticker", "source", "confidence"]].copy()
saved_view = saved_view.rename(
    columns={
        "ticker": "saved_ticker",
        "source": "saved_source",
        "confidence": "saved_confidence",
    }
)
eff_view = effective_mapping[["asset_id", "ticker", "source", "confidence", "exchange", "price_scale"]].copy()
eff_view = eff_view.rename(
    columns={
        "ticker": "effective_ticker",
        "source": "effective_source",
        "confidence": "effective_confidence",
    }
)
fallback_applied = saved_view.merge(eff_view, on="asset_id", how="left")
fallback_applied = fallback_applied[
    fallback_applied["saved_ticker"].astype(str).str.strip().eq("")
    & fallback_applied["effective_ticker"].astype(str).str.strip().ne("")
].copy()

st.subheader("Runtime Fallback Mappings")
if fallback_applied.empty:
    st.caption("No runtime fallback mappings are currently applied.")
else:
    st.caption("These assets are still unmapped in saved table but mapped at runtime by built-in defaults.")
    st.dataframe(
        fallback_applied[
            [
                "asset_id",
                "asset_name",
                "effective_ticker",
                "exchange",
                "price_scale",
                "effective_source",
                "effective_confidence",
            ]
        ].sort_values("asset_name"),
        use_container_width=True,
        hide_index=True,
    )

if not anomalies.empty:
    st.error("Valuation anomalies detected")
    st.dataframe(anomalies, use_container_width=True, hide_index=True)
    can_apply = (anomalies["suggested_scale"] != anomalies["current_scale"]).any()
    if can_apply and st.button("Apply suggested price_scale fixes"):
        updated = edited.copy()
        suggestions = anomalies.set_index("asset_id")["suggested_scale"].to_dict()
        updated["price_scale"] = updated.apply(lambda r: suggestions.get(r["asset_id"], r["price_scale"]), axis=1)
        save_mapping(updated)
        st.success("Applied suggested price_scale values and saved mapping")
        st.rerun()

st.subheader("Ticker Candidate Helper")
unmapped = edited[edited["ticker"].astype(str).str.strip().eq("")]
if unmapped.empty:
    st.success("All assets are mapped.")
else:
    asset_choice = st.selectbox("Pick unmapped asset", unmapped["asset_name"].tolist())
    asset_row = unmapped[unmapped["asset_name"].eq(asset_choice)].iloc[0]
    buy_rows = tx[
        tx["Asset Id"].eq(asset_row["asset_id"])
        & tx["Transfer Type"].eq("ASSET_TRADE_BUY")
        & tx["Asset Price"].notna()
    ]
    if buy_rows.empty:
        st.caption("No buy price found in CSV for this asset.")
    else:
        first_buy = buy_rows.sort_values("date").iloc[0]
        target_price = float(first_buy["Asset Price"])
        target_date = first_buy["date"].date()
        st.caption(f"Reference point: {target_date} at {target_price:.4f} {asset_row['asset_currency']}")

        if st.button("Suggest ticker candidates"):
            suggestions = suggest_candidates(asset_choice, target_price, target_date)
            st.session_state["qa_ticker_suggestions"] = suggestions
            st.session_state["qa_ticker_suggest_asset_id"] = asset_row["asset_id"]

        suggestions = st.session_state.get("qa_ticker_suggestions")
        if isinstance(suggestions, pd.DataFrame) and not suggestions.empty and st.session_state.get("qa_ticker_suggest_asset_id") == asset_row["asset_id"]:
            st.dataframe(suggestions, use_container_width=True, hide_index=True)
            options = [f"{r.ticker} | {r.exchange} | err={r.relative_error:.4f}" for _, r in suggestions.iterrows()]
            picked = st.selectbox("Pick candidate", options)
            if st.button("Apply selected candidate"):
                ticker = picked.split(" | ")[0].strip()
                idx = edited.index[edited["asset_id"].eq(asset_row["asset_id"])]
                if len(idx) > 0:
                    edited.loc[idx, "ticker"] = ticker
                    edited.loc[idx, "source"] = "price_match"
                    edited.loc[idx, "confidence"] = "medium"
                    save_mapping(edited)
                    st.success(f"Applied {ticker} to {asset_row['asset_name']}")
                    st.rerun()

st.subheader("Current Mapping Snapshot")
st.dataframe(edited.sort_values(["confidence", "asset_name"]), use_container_width=True, hide_index=True)
