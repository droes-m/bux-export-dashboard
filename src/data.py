from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

DATE_COL = "Transaction Time (CET)"
NUMERIC_COLS = [
    "Transaction Amount",
    "Cash Balance Amount",
    "Asset Quantity",
    "Asset Price",
    "Exchange Rate",
    "Profit And Loss Amount",
    "Dividend Gross Amount",
    "Dividend Net Amount",
    "Dividend Tax Amount",
]


@dataclass
class PortfolioData:
    transactions: pd.DataFrame
    security_master: pd.DataFrame


def _read_csv(input_obj: Any) -> pd.DataFrame:
    if isinstance(input_obj, (str, Path)):
        return pd.read_csv(input_obj)

    if hasattr(input_obj, "read"):
        raw = input_obj.read()
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return pd.read_csv(BytesIO(raw))

    raise TypeError("Unsupported input type for CSV loading")


def load_transactions(input_obj: Any) -> pd.DataFrame:
    df = _read_csv(input_obj)
    missing = [c for c in [DATE_COL, "Asset Id", "Asset Name"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    if df[DATE_COL].isna().all():
        raise ValueError("Could not parse any transaction timestamps")

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(DATE_COL).reset_index(drop=True)
    df["date"] = df[DATE_COL].dt.floor("D")

    transfer = df.get("Transfer Type", pd.Series(index=df.index, dtype="object")).fillna("")
    qty = df.get("Asset Quantity", pd.Series(index=df.index, dtype="float64")).fillna(0.0)
    df["signed_quantity"] = 0.0
    df.loc[transfer.eq("ASSET_TRADE_BUY"), "signed_quantity"] = qty
    df.loc[transfer.eq("ASSET_TRADE_SELL"), "signed_quantity"] = -qty

    return df


def build_security_master(df: pd.DataFrame) -> pd.DataFrame:
    rows = df[df["Asset Id"].notna()].copy()
    rows = rows.rename(
        columns={
            "Asset Id": "asset_id",
            "Asset Name": "asset_name",
            "Asset Currency": "asset_currency",
        }
    )

    base = (
        rows.loc[:, ["asset_id", "asset_name", "asset_currency"]]
        .drop_duplicates()
        .sort_values(["asset_name", "asset_id"])
        .reset_index(drop=True)
    )

    # Some BUX rows have missing asset currency; infer from transaction currency on priced asset rows.
    infer_rows = rows[(rows["asset_currency"].isna() | rows["asset_currency"].eq("")) & rows["Asset Price"].notna()]
    infer = (
        infer_rows.loc[:, ["asset_id", "Transaction Currency"]]
        .dropna()
        .groupby("asset_id")["Transaction Currency"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
        .reset_index(name="inferred_ccy")
    )
    if not infer.empty:
        base = base.merge(infer, on="asset_id", how="left")
        base["asset_currency"] = base["asset_currency"].where(base["asset_currency"].astype(str).str.strip().ne(""), base["inferred_ccy"])
        base = base.drop(columns=["inferred_ccy"])

    base["asset_currency"] = base["asset_currency"].fillna("")
    return base
