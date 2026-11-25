"""Download daily prices (raw and adjusted close) for all firms and benchmark indices from Yahoo Finance."""
from datetime import date

import pandas as pd
import yfinance as yf

from config import FIRMS, INDICES, PRICE_START, RAW

OUT = RAW / "prices"
OUT.mkdir(parents=True, exist_ok=True)

END = (pd.Timestamp(date.today()) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def fetch(ticker):
    df = yf.download(ticker, start=PRICE_START, end=END, auto_adjust=False,
                     actions=True, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns=str.lower).rename(columns={"adj close": "adj_close", "stock splits": "splits"})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


manifest = []
targets = [(f[0], f[3]) for f in FIRMS] + [(i[0], i[2]) for i in INDICES]
for sid, ticker in targets:
    df = fetch(ticker)
    path = OUT / f"{sid}.csv"
    df.to_csv(path, index=False)
    manifest.append({
        "id": sid, "ticker": ticker, "rows": len(df),
        "first_date": df["date"].min() if len(df) else None,
        "last_date": df["date"].max() if len(df) else None,
        "downloaded": date.today().isoformat(),
    })
    print(f"{sid:10s} {ticker:15s} rows={len(df):5d} {manifest[-1]['first_date']} -> {manifest[-1]['last_date']}")

pd.DataFrame(manifest).to_csv(OUT / "_manifest.csv", index=False)
empty = [m["id"] for m in manifest if m["rows"] == 0]
if empty:
    print("NO DATA:", empty)
