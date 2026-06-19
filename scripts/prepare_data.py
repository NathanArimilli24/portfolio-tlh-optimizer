#!/usr/bin/env python3
"""
prepare_data.py
===============
One-time data preparation for the Portfolio TLH Optimizer.

Takes the raw Vise market-data extract (S&P Capital IQ) and produces the files
the app and backtest actually consume:

  1. data/price_data.parquet  - full price history, 6 columns, zstd-compressed.
                                The 545MB raw CSV becomes a ~14MB parquet that
                                ships with the repo, so the app and the full
                                backtest run from a clean clone with no download.
  2. data/dividend_data.csv   - dividends WITH a TICKERSYMBOL column added.
                                The raw extract only has TRADINGITEMID, which
                                silently disables DRIP in the engine.

Usage:
    python scripts/prepare_data.py --raw "/path/to/Data"

The raw extract (price_data.csv ~545MB) is git-ignored; this script regenerates
everything the repo needs from it.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import pandas as pd

PRICE_COLS = ["TRADINGITEMID", "TICKERSYMBOL", "PRICEDATE",
              "PRICECLOSE", "PRICEMID", "TRADINGITEMSTATUSID"]


def _read_price_csv(csv_path: Path) -> pd.DataFrame:
    print(f"Reading {csv_path.name} (this is the 545MB file, ~1-2 min) ...", flush=True)
    parts = []
    for i, ch in enumerate(pd.read_csv(csv_path, usecols=PRICE_COLS,
                                       chunksize=2_000_000, low_memory=False)):
        parts.append(ch)
        print(f"  chunk {i + 1}: {len(ch):,} rows", flush=True)
    df = pd.concat(parts, ignore_index=True)
    df["TICKERSYMBOL"] = df["TICKERSYMBOL"].astype(str).str.strip().str.upper()
    df["PRICEDATE"] = pd.to_datetime(df["PRICEDATE"], errors="coerce")
    print(f"Loaded {len(df):,} rows, {df['TICKERSYMBOL'].nunique()} tickers", flush=True)
    return df


def build_full_parquet(price_df: pd.DataFrame, out: Path) -> None:
    price_df.to_parquet(out, index=False, compression="zstd")
    mb = out.stat().st_size / 1e6
    print(f"WROTE {out}  ({mb:.1f} MB)", flush=True)


def map_dividends(price_df: pd.DataFrame, raw_div: Path, out: Path) -> None:
    """Add a TICKERSYMBOL column to the dividend extract via TRADINGITEMID."""
    div = pd.read_csv(raw_div)
    div = div.loc[:, [c for c in div.columns if not c.startswith("Unnamed")]]
    # Most-recent ticker per trading item id (tickers can change over time).
    id_map = (price_df.dropna(subset=["PRICEDATE"])
              .sort_values("PRICEDATE")
              .groupby("TRADINGITEMID")["TICKERSYMBOL"].last())
    div["TICKERSYMBOL"] = div["TRADINGITEMID"].map(id_map)
    mapped = div["TICKERSYMBOL"].notna().sum()
    div.to_csv(out, index=False)
    print(f"WROTE {out}  ({mapped:,}/{len(div):,} dividend rows mapped to a ticker)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--raw", default=str(here.parent / "Data"),
                    help="Folder with raw price_data.csv / dividend_data.csv")
    ap.add_argument("--out", default=str(here / "data"), help="Output data/ folder")
    args = ap.parse_args()

    raw = Path(args.raw)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    price_df = _read_price_csv(raw / "price_data.csv")
    build_full_parquet(price_df, out / "price_data.parquet")
    map_dividends(price_df, raw / "dividend_data.csv", out / "dividend_data.csv")
    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
