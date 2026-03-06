from __future__ import annotations

from pathlib import Path

import pandas as pd

MAP_COLUMNS = [
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


def load_or_init_security_map(security_master: pd.DataFrame, map_path: str | Path) -> pd.DataFrame:
    map_path = Path(map_path)
    map_path.parent.mkdir(parents=True, exist_ok=True)

    if map_path.exists():
        current = pd.read_csv(map_path)
    else:
        current = pd.DataFrame(columns=MAP_COLUMNS)

    for col in MAP_COLUMNS:
        if col not in current.columns:
            current[col] = ""

    merged = security_master.merge(
        current[MAP_COLUMNS],
        how="left",
        on=["asset_id", "asset_name", "asset_currency"],
    )

    merged = merged.fillna("")
    merged["price_scale"] = pd.to_numeric(merged["price_scale"], errors="coerce").fillna(1.0)
    merged["confidence"] = merged["confidence"].replace("", "unmapped")
    merged["source"] = merged["source"].replace("", "pending")
    merged = merged[MAP_COLUMNS].drop_duplicates(subset=["asset_id"], keep="first")
    return merged.sort_values(["confidence", "asset_name"]).reset_index(drop=True)


def save_security_map(mapping_df: pd.DataFrame, map_path: str | Path) -> None:
    map_path = Path(map_path)
    out = mapping_df.copy()
    for col in MAP_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out = out[MAP_COLUMNS].sort_values(["asset_name", "asset_id"]) 
    out.to_csv(map_path, index=False)
