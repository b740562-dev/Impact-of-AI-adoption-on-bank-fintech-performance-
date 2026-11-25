"""Phase 1 dataset: level x FY for (a) sector = PSU + Private, (b) Private, (c) PSU; FY2011-FY2025.

Outcomes from RBI group aggregates (Table 1/2/6 subtotal rows): ROE, ROA, GNPA (same formulas as bank level;
sector = PSU and Private aggregates summed before ratios). AI intensity = total-assets-weighted mean of ai_kw
over the panel banks in the level with non-missing ai_kw. GDP growth merged from data/interim/gdp_growth.csv if
present (RBI DBIE); otherwise left NA and reported.
"""
import numpy as np
import pandas as pd

from config import FIRMS, INTERIM

FY = (2010, 2025)  # FY2010 kept so that ai_kw(t-1) exists for FY2011
SHOCKS = {"demon": [2017], "aqr": [2016, 2017, 2018], "covid": [2021]}
SUM_COLS = ["capital", "reserves", "total_assets", "pat", "gross_npa", "net_npa", "advances"]

grp = pd.read_csv(INTERIM / "rbi_group_financials.csv")
grp = grp[grp["fy"].between(FY[0] - 1, FY[1])]
# RBI reports a "Public Sector Banks" subtotal only from FY2018; before that PSU = Nationalised + SBI & associates.
psu_direct = grp[(grp["group_id"] == "PSU") & grp["total_assets"].notna()]  # header-only rows have no amounts
psu_sum = (grp[grp["group_id"].isin(["Nationalised", "SBI_group"])].groupby("fy")[SUM_COLS].sum(min_count=2)
           .reset_index())
psu_sum = psu_sum[~psu_sum["fy"].isin(psu_direct["fy"])]
psu = pd.concat([psu_direct[["fy"] + SUM_COLS], psu_sum], ignore_index=True).assign(level="PSU")
priv = grp.loc[grp["group_id"] == "Private", ["fy"] + SUM_COLS].assign(level="Private")
both = pd.concat([psu, priv], ignore_index=True)
assert not both.duplicated(["level", "fy"]).any()
sector = both.groupby("fy")[SUM_COLS].sum(min_count=2).reset_index().assign(level="Sector")
lvl = pd.concat([both, sector], ignore_index=True)
print("PSU source by FY: subtotal row", sorted(psu_direct.fy), "| Nationalised + SBI group", sorted(psu_sum.fy))
lvl = lvl.sort_values(["level", "fy"])
g = lvl.groupby("level")
lvl["equity"] = lvl["capital"] + lvl["reserves"]
prev = g["fy"].shift(1) == lvl["fy"] - 1
lvl["roe"] = np.where(prev, lvl["pat"] / ((lvl["equity"] + g["equity"].shift(1)) / 2) * 100, np.nan)
lvl["roa"] = np.where(prev, lvl["pat"] / ((lvl["total_assets"] + g["total_assets"].shift(1)) / 2) * 100, np.nan)
lvl["gnpa_ratio"] = lvl["gross_npa"] / (lvl["advances"] + lvl["gross_npa"] - lvl["net_npa"]) * 100

# total-assets-weighted ai_kw over panel banks in each level
types = {f[0]: f[2] for f in FIRMS if f[4]}
kw = pd.read_csv(INTERIM / "ai_kw.csv", usecols=["bank_id", "fy", "ai_kw"])
fin = pd.read_csv(INTERIM / "rbi_bank_financials.csv", usecols=["bank_id", "fy", "total_assets"])
b = kw.merge(fin, on=["bank_id", "fy"], how="left", validate="one_to_one")
b = b[b["bank_id"].map(types).notna() & ~((b["bank_id"] == "IDFCFIRST") & (b["fy"] < 2019))]
b["type"] = b["bank_id"].map(types)
b = b.dropna(subset=["ai_kw", "total_assets"])


def wavg(d):
    return pd.Series({"ai_kw_w": np.average(d["ai_kw"], weights=d["total_assets"]), "n_banks": len(d)})


w = pd.concat([b.groupby(["type", "fy"]).apply(wavg, include_groups=False).reset_index().rename(columns={"type": "level"}),
               b.groupby("fy").apply(wavg, include_groups=False).reset_index().assign(level="Sector")],
              ignore_index=True)
n0 = len(lvl)
lvl = lvl.merge(w, on=["level", "fy"], how="left", validate="one_to_one")
assert len(lvl) == n0
lvl = lvl.sort_values(["level", "fy"])
lvl["ai_kw_w_lag1"] = lvl.groupby("level")["ai_kw_w"].shift(1)

gdp_path = INTERIM / "gdp_growth.csv"
if gdp_path.exists():
    gdp = pd.read_csv(gdp_path)[["fy", "gdp_growth"]]
    lvl = lvl.merge(gdp, on="fy", how="left", validate="many_to_one")
else:
    lvl["gdp_growth"] = np.nan
for k, yrs in SHOCKS.items():
    lvl[k] = lvl["fy"].isin(yrs).astype(int)
lvl["post_fy2017"] = (lvl["fy"] >= 2017).astype(int)

out = lvl[lvl["fy"].between(2011, FY[1])]
cols = ["level", "fy", "roe", "roa", "gnpa_ratio", "ai_kw_w", "ai_kw_w_lag1", "n_banks", "gdp_growth",
        "demon", "aqr", "covid", "post_fy2017", "total_assets", "pat", "equity"]
out = out[cols]
assert not out.duplicated(["level", "fy"]).any()
out.to_csv(INTERIM / "phase1_levels.csv", index=False)

print(out.round(2).to_string(index=False))
print("\nmissing gdp_growth:", out["gdp_growth"].isna().sum(), "rows",
      "(data/interim/gdp_growth.csv not found)" if not gdp_path.exists() else "")
print("\nPre (FY2011-16) vs post (FY2017-25) means:")
print(out.groupby(["level", "post_fy2017"])[["ai_kw_w", "roe", "roa", "gnpa_ratio"]].mean().round(2).to_string())
