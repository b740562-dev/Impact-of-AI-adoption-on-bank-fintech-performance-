"""Baseline bank characteristics (pre-period FY2011-FY2015): Z-score moderator.

z_raw = (mean ROA + mean equity/assets) / SD(ROA), ROA and equity/assets in percent, over FY2011-FY2015.
zscore_std = z_raw standardised across panel banks (mean 0, SD 1). Banks without all five years -> NA.
"""
import numpy as np
import pandas as pd

from config import INTERIM

BASE = (2011, 2015)

fin = pd.read_csv(INTERIM / "rbi_bank_financials.csv", usecols=["bank_id", "bank_type", "fy", "roa", "equity",
                                                                 "total_assets"])
b = fin[fin["fy"].between(*BASE)].copy()
b["eq_assets"] = b["equity"] / b["total_assets"] * 100
g = b.groupby(["bank_id", "bank_type"])
base = g.agg(n_years=("roa", "count"), roa_mean=("roa", "mean"), roa_sd=("roa", "std"),
             eq_assets_mean=("eq_assets", "mean")).reset_index()
full = base["n_years"] == BASE[1] - BASE[0] + 1
base["z_raw"] = np.where(full, (base["roa_mean"] + base["eq_assets_mean"]) / base["roa_sd"], np.nan)
base["zscore_std"] = (base["z_raw"] - base["z_raw"].mean()) / base["z_raw"].std()
assert base["bank_id"].is_unique
base.to_csv(INTERIM / "baseline_bank.csv", index=False)

print(f"baseline window FY{BASE[0]}-FY{BASE[1]}; banks: {len(base)}, with full window: {full.sum()}")
print(base.sort_values("z_raw", ascending=False).round(3).to_string(index=False))
print("\nmean z_raw by type:", base.groupby("bank_type")["z_raw"].mean().round(2).to_dict())
