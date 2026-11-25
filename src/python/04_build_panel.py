"""Bank x FY panel (spec §3b, §4): FY2011-FY2026, 25 banks (IDFC First from FY2019). Output data/final/panel.parquet.

Accounting variables end FY2025 (spec_changes 2026-11-25). Controls lagged one year. Missing values stay NA.
Merge diagnostics and the missing-value table go to logs/panel.log; summary <= 20 lines to stdout.
"""
import numpy as np
import pandas as pd

from config import FINAL, FIRMS, INTERIM, RAW

ROOT = RAW.parent.parent
LOG = ROOT / "logs" / "panel.log"
LOG.parent.mkdir(exist_ok=True)
log = open(LOG, "w", encoding="utf-8")
PANEL = {f[0]: f[2] for f in FIRMS if f[4]}
FY0, FY1 = 2011, 2026
MERGERS = {("SBI", 2018), ("BOB", 2020), ("PNB", 2021), ("CANARA", 2021), ("UNION", 2021), ("INDIAN", 2021),
           ("HDFC", 2024), ("IDFCFIRST", 2019)}

grid = pd.MultiIndex.from_product([list(PANEL), range(2009, FY1 + 1)], names=["bank_id", "fy"]).to_frame(index=False)
grid["bank_type"] = grid["bank_id"].map(PANEL)
grid["psu"] = (grid["bank_type"] == "PSU").astype(int)


def merge(df, other, keys, name):
    n0 = len(df)
    assert not other.duplicated(keys).any(), f"{name}: duplicate keys"
    out = df.merge(other, on=keys, how="left", validate="many_to_one" if keys == ["bank_id"] else "one_to_one")
    assert len(out) == n0, f"{name}: row count changed {n0} -> {len(out)}"
    matched = out[other.columns.difference(keys)[0]].notna().sum()
    print(f"merge {name:16s} rows {n0} -> {len(out)}; non-missing {other.columns.difference(keys)[0]}: {matched}", file=log)
    return out


fin = pd.read_csv(INTERIM / "rbi_bank_financials.csv")
fin = fin[["bank_id", "fy", "roe", "roa", "ln_assets", "total_assets", "crar", "ldr", "liquidity_ratio",
           "gnpa_ratio", "cost_income", "pat", "equity"]]
p = merge(grid, fin, ["bank_id", "fy"], "financials")
ret = pd.read_csv(INTERIM / "returns_fy.csv").rename(columns={"id": "bank_id"})[["bank_id", "fy", "stock_ret_pct"]]
p = merge(p, ret, ["bank_id", "fy"], "returns")
mc = pd.read_csv(INTERIM / "market_cap_fy.csv")[["bank_id", "fy", "tobins_q", "market_cap_cr"]]
p = merge(p, mc, ["bank_id", "fy"], "market_cap")
kw = pd.read_csv(INTERIM / "ai_kw.csv")[["bank_id", "fy", "ai_kw", "ai_kw_z", "ai_kw_ln"]]
p = merge(p, kw, ["bank_id", "fy"], "ai_kw")
cum = pd.read_csv(INTERIM / "ai_events_cum.csv")
p = merge(p, cum, ["bank_id", "fy"], "ai_events_cum")
pca = pd.read_csv(INTERIM / "pca_bank_fy.csv")
p = merge(p, pca, ["bank_id", "fy"], "pca")
p[["pca", "pca_months"]] = p[["pca", "pca_months"]].fillna(0).astype(int)  # banks never under PCA = 0
base = pd.read_csv(INTERIM / "baseline_bank.csv")[["bank_id", "zscore_std", "z_raw"]]
p = merge(p, base, ["bank_id"], "baseline_z")
fnd = pd.read_csv(RAW / "founding_years.csv")[["bank_id", "founded_year"]]
p = merge(p, fnd, ["bank_id"], "founding")
ad = pd.read_csv(INTERIM / "adoption.csv").drop(columns=["bank_type", "first_event_id", "first_event_date"])
p = merge(p, ad, ["bank_id"], "adoption")

calls = INTERIM / "ai_calls.csv"  # optional proxy 6 (built by 09_transcripts.py)
if calls.exists():
    p = merge(p, pd.read_csv(calls)[["bank_id", "fy", "ai_calls"]], ["bank_id", "fy"], "ai_calls")
p = p.sort_values(["bank_id", "fy"]).reset_index(drop=True)
g = p.groupby("bank_id")
# ---- lags (computed on the full grid so FY2011 lags use FY2010 data) ----
for v in ["ln_assets", "crar", "ldr", "liquidity_ratio", "gnpa_ratio", "pca", "ai_kw", "ai_kw_z", "ai_kw_ln",
          "ai_events_cum", "cost_income"]:
    p[f"{v}_l1"] = g[v].shift(1)
p["ai_kw_l2"] = g["ai_kw"].shift(2)
p["profit_growth"] = (p["pat"] / g["pat"].shift(1) - 1) * 100
p.loc[g["pat"].shift(1) <= 0, "profit_growth"] = np.nan  # undefined when last year's PAT <= 0
p["profit_growth_l1"] = g["profit_growth"].shift(1)

# ---- treatment indicators ----
for k in ["main", "alt1", "alt2_p50", "alt2_p75"]:
    c = f"adopt_fy_{k}"
    p[f"post_adopt{'' if k == 'main' else '_' + k}"] = ((p["fy"] >= p[c]) & p[c].notna()).astype(int)
    p[f"gname_{k}"] = p[c].fillna(0).astype(int)  # did::att_gt convention: 0 = never treated

# ---- baseline and shocks ----
p["baseline_age"] = 2011 - p["founded_year"]
b11 = p.loc[p["fy"] == 2011].set_index("bank_id")["ln_assets"]
first = p.dropna(subset=["ln_assets"]).loc[lambda d: d["fy"] >= 2011].groupby("bank_id")["ln_assets"].first()
p["baseline_ln_assets"] = p["bank_id"].map(b11.combine_first(first))  # IDFC First: first available FY
p["covid"] = (p["fy"] == 2021).astype(int)
p["demon"] = (p["fy"] == 2017).astype(int)
p["post_chatgpt"] = (p["fy"] >= 2023).astype(int)
p["aqr_psu"] = (p["fy"].between(2016, 2018) & (p["psu"] == 1)).astype(int)
p["merger_year"] = [int((b, f) in MERGERS) for b, f in zip(p["bank_id"], p["fy"])]
p["yes_reconstruction"] = ((p["bank_id"] == "YES") & (p["fy"] == 2020)).astype(int)

# ---- sample ----
p = p[p["fy"].between(FY0, FY1) & ~((p["bank_id"] == "IDFCFIRST") & (p["fy"] < 2019))].copy()
assert not p.duplicated(["bank_id", "fy"]).any()
FINAL.mkdir(parents=True, exist_ok=True)
p.to_parquet(FINAL / "panel.parquet", index=False)

key = ["roe", "roa", "stock_ret_pct", "tobins_q", "ai_kw_l1", "ln_assets_l1", "crar_l1", "ldr_l1",
       "liquidity_ratio_l1", "gnpa_ratio_l1", "pca_l1", "zscore_std", "baseline_age"]
miss = p.groupby("fy")[key].apply(lambda d: d.isna().sum())
print("\nmissing values by FY:\n" + miss.to_string(), file=log)
print(f"panel: {len(p)} bank-FYs, {p.bank_id.nunique()} banks, FY{p.fy.min()}-FY{p.fy.max()}, {p.shape[1]} columns")
print("non-missing:", {k: int(p[k].notna().sum()) for k in ["roe", "stock_ret_pct", "tobins_q", "ai_kw_l1", "crar_l1"]})
print(f"treated (main) banks: {(p.groupby('bank_id')['post_adopt'].max() == 1).sum()}; pca=1 bank-FYs: {p['pca'].sum()}")
print(f"details: {LOG}")
