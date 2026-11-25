"""Clean daily prices and build fiscal-year total returns (1 Apr to 31 Mar, adjusted close)."""
import numpy as np
import pandas as pd

from config import FIRMS, INDICES, INTERIM, RAW, fiscal_year

SRC = RAW / "prices"
INTERIM.mkdir(parents=True, exist_ok=True)
EXTREME = 0.30  # |daily simple return| flagged for manual review

manifest = pd.read_csv(SRC / "_manifest.csv")
meta = pd.DataFrame(
    [(f[0], f[2], f[3], "firm") for f in FIRMS] + [(i[0], "Index", i[2], "index") for i in INDICES],
    columns=["id", "type", "ticker", "kind"],
)

frames = []
for sid in meta["id"]:
    df = pd.read_csv(SRC / f"{sid}.csv", parse_dates=["date"])
    dl_date = pd.Timestamp(manifest.loc[manifest["id"] == sid, "downloaded"].iloc[0])
    df = df[df["date"] < dl_date]  # drop the possibly incomplete download-day bar
    df["id"] = sid
    frames.append(df[["id", "date", "close", "adj_close", "volume"]])
px = pd.concat(frames, ignore_index=True).sort_values(["id", "date"])

assert not px.duplicated(["id", "date"]).any(), "duplicate id x date"
n_na = px["adj_close"].isna().sum()
px = px.dropna(subset=["adj_close"])
px = px[px["adj_close"] > 0]

px["ret"] = px.groupby("id")["adj_close"].pct_change()
px["zero_volume"] = (px["volume"] == 0) & px["id"].isin(meta.loc[meta.kind == "firm", "id"])
px["extreme_ret"] = px["ret"].abs() > EXTREME
px["fy"] = fiscal_year(px["date"].dt)

px.to_parquet(INTERIM / "prices_daily.parquet", index=False)

# Fiscal-year total return: last adjusted close of FY vs last adjusted close of prior FY.
# A FY is valid only if the series exists by the prior FY's last trading week (i.e. listed before 1 Apr).
last = px.groupby(["id", "fy"]).agg(p_end=("adj_close", "last"), d_end=("date", "last"),
                                    d_first=("date", "first"), n_days=("date", "size")).reset_index()
last["p_start"] = last.groupby("id")["p_end"].shift(1)
last["d_start"] = last.groupby("id")["d_end"].shift(1)
last["prev_fy"] = last.groupby("id")["fy"].shift(1)
fy_end = pd.to_datetime((last["fy"]).astype(str) + "-03-31")
complete = (last["prev_fy"] == last["fy"] - 1) & (last["d_start"] >= fy_end - pd.DateOffset(years=1) - pd.Timedelta(days=7)) \
           & (last["d_end"] >= fy_end - pd.Timedelta(days=7))
last["ret_fy"] = np.where(complete, (last["p_end"] / last["p_start"] - 1) * 100, np.nan)
extreme_fy = px.loc[px["extreme_ret"]].groupby(["id", "fy"]).size().rename("n_extreme_days").reset_index()
last = last.merge(extreme_fy, on=["id", "fy"], how="left", validate="one_to_one")
last["n_extreme_days"] = last["n_extreme_days"].fillna(0).astype(int)
ret_fy = last.loc[(last["fy"] >= 2010) & (last["fy"] <= 2026),
                  ["id", "fy", "ret_fy", "n_days", "d_start", "d_end", "n_extreme_days"]]
ret_fy = ret_fy.rename(columns={"ret_fy": "stock_ret_pct"})
ret_fy["d_start"] = ret_fy["d_start"].dt.strftime("%Y-%m-%d")
ret_fy["d_end"] = ret_fy["d_end"].dt.strftime("%Y-%m-%d")
assert not ret_fy.duplicated(["id", "fy"]).any()
ret_fy.to_csv(INTERIM / "returns_fy.csv", index=False)

# Diagnostics
print(f"daily rows: {len(px):,}  dropped NA adj_close: {n_na}")
summary = px.groupby("id").agg(first=("date", "min"), last=("date", "max"), n=("date", "size"),
                               zero_vol=("zero_volume", "sum"), extreme=("extreme_ret", "sum"))
print(summary.to_string())
flags = px.loc[px["extreme_ret"], ["id", "date", "close", "adj_close", "ret"]]
flags["date"] = flags["date"].dt.strftime("%Y-%m-%d")
flags.to_csv(INTERIM / "price_flags_extreme.csv", index=False)
print(f"\nextreme daily returns (|r|>{EXTREME:.0%}): {len(flags)} -> data/interim/price_flags_extreme.csv")
print(flags.to_string(index=False))
wide = ret_fy.pivot(index="fy", columns="id", values="stock_ret_pct")
print("\nFY total return coverage (non-missing firms per FY):")
print(wide.notna().sum(axis=1).to_string())
