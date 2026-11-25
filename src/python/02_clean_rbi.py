"""Parse RBI Statistical Tables Relating to Banks in India (DBIE Excel exports) into long and bank-year files."""
import re
import warnings

import numpy as np
import pandas as pd

from config import FIRMS, INTERIM, RAW, RBI_GROUPS, RBI_NAMES

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
SRC = RAW / "rbi"

FILES = {
    "T01": ("T01_liabilities_assets.xlsx", "amount"),
    "T02": ("T02_earnings_expenses.xlsx", "amount"),
    "T03": ("T03_crar.xlsx", "ratio"),
    "T06": ("T06_npa_movement.xlsx", "amount"),
    "T11": ("T11_select_ratios.xlsx", "ratio"),
}


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def to_num(v, kind):
    if isinstance(v, str):
        v = v.strip().replace(",", "")
        if v == "-":
            # RBI convention: "-" = nil. Zero for amounts; left NA for ratios.
            return 0.0 if kind == "amount" else np.nan
        if v in ("..", "", "NA", "N.A."):
            return np.nan
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def to_fy(v):
    if pd.isna(v):
        return np.nan
    if isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, "year"):
        return pd.Timestamp(v).year  # "as on March 31" of year t = FY t
    m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?", str(v).strip())
    if not m:
        return np.nan
    return int(m.group(1)) + (1 if m.group(2) else 0)


def parse_sheet(df, table, sheet, kind):
    col1 = df.iloc[:, 1].astype(str).str.strip()
    hdr = col1[col1 == "Year"].index[0]
    first_data = df.index[(df.index > hdr) & df.iloc[:, 2].notna()][0]
    head = df.iloc[hdr:first_data, 3:].copy()
    head = head.apply(lambda r: r.ffill() if r.name < first_data - 1 else r, axis=1)  # spread group labels
    labels = [" | ".join(norm(x) for x in head[c].tolist() if pd.notna(x) and not re.fullmatch(r"\(\d+\)", norm(x)))
              for c in head.columns]
    # Roman-numeral sub-items such as "(i) Government securities" repeat under different parents.
    parent, unique = None, []
    for lab in labels:
        if re.match(r"^\d", lab):
            parent = lab
        unique.append(f"{parent} > {lab}" if lab.startswith("(") and parent else lab)
    labels = unique
    body = df.iloc[first_data:].copy()
    body["fy"] = body.iloc[:, 1].map(to_fy).ffill()
    # Trailing * / # are RBI footnote markers (e.g. merged entities in T06).
    body["rbi_name"] = body.iloc[:, 2].map(lambda x: re.sub(r"[*#]+$", "", norm(x)).strip().upper() if pd.notna(x) else np.nan)
    body = body[body["rbi_name"].notna()]
    rows = []
    for j, lab in zip(head.columns, labels):
        part = pd.DataFrame({"fy": body["fy"], "rbi_name": body["rbi_name"], "item": lab,
                             "value": body[j].map(lambda v: to_num(v, kind))})
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    out["table"], out["sheet"] = table, sheet
    return out


frames = []
for table, (fname, kind) in FILES.items():
    for sheet, df in pd.read_excel(SRC / fname, sheet_name=None, header=None).items():
        frames.append(parse_sheet(df, table, sheet, kind))
long = pd.concat(frames, ignore_index=True)
long = long[long["fy"].notna()].copy()
long["fy"] = long["fy"].astype(int)
long["bank_id"] = long["rbi_name"].map(RBI_NAMES)
long["group_id"] = long["rbi_name"].map(RBI_GROUPS)

# Group subtotal rows that are entirely empty (layout rows in T03) carry no data.
long = long[~(long["group_id"].notna() & long["value"].isna())]
dups = long.duplicated(["table", "fy", "rbi_name", "item"], keep=False)
if dups.any():
    print("WARNING duplicate table x fy x bank x item rows:", dups.sum())
    print(long[dups].head(20).to_string())
long.to_parquet(INTERIM / "rbi_long.parquet", index=False)
print(f"rbi_long: {len(long):,} rows, {long['rbi_name'].nunique()} names, FY{long.fy.min()}-FY{long.fy.max()}")

# ---------- select variables ----------
def pick(table, pattern, name, how="first"):
    m = long[(long["table"] == table) & long["item"].str.contains(pattern, regex=True, case=False)]
    items = sorted(m["item"].unique())
    print(f"  {name:22s} <- {table}: {items}")
    return m.groupby(["rbi_name", "fy"])["value"].sum(min_count=1).rename(name) if how == "sum" \
        else m.groupby(["rbi_name", "fy"])["value"].first().rename(name)


print("variable mapping:")
series = [
    pick("T01", r"^1\. Capital$", "capital"),
    pick("T01", r"^2\. Reserves and Surplus$", "reserves"),
    pick("T01", r"^3\. Deposits$", "deposits"),
    pick("T01", r"^4\. Borrowings$", "borrowings"),
    pick("T01", r"^Total Liabilities$", "total_liabilities_incl_equity"),
    pick("T01", r"^Total Assets$", "total_assets"),
    pick("T01", r"^1\. Cash in hand$", "cash"),
    pick("T01", r"^2\. Balances with RBI$", "bal_rbi"),
    pick("T01", r"^3\. Balances with banks in India$", "bal_banks_india"),
    pick("T01", r"^4\. Money at call and short notice$", "call_money"),
    pick("T01", r"^5\. Balances with banks outside India$", "bal_banks_abroad"),
    pick("T01", r"^6\. Investments$", "investments"),
    pick("T01", r"^7\. Advances$", "advances"),
    pick("T02", r"^Total \(I\)$", "interest_income"),
    pick("T02", r"Total \(II\)$", "other_income"),
    pick("T02", r"Total \(I\+II\)$", "total_income"),
    pick("T02", r"Total \(III\)$", "interest_expended"),
    pick("T02", r"Payments to and provisions for employees", "wage_bill"),
    pick("T02", r"Total \(IV\)$", "opex"),
    pick("T02", r"Net Interest Income", "nii"),
    pick("T02", r"Provisions and Contingencies$", "provisions"),
    pick("T02", r"Operating Profit", "operating_profit"),
    pick("T02", r"Profit \(Loss\) during the year", "pat"),
    pick("T06", r"^Gross NPAs \| Closing Balance$", "gross_npa"),
    pick("T06", r"^Net NPAs \| Closing Balance$", "net_npa"),
    pick("T03", r"^Basel-I \| Total$", "crar_b1"),
    pick("T03", r"^Basel-II \| Total$", "crar_b2"),
    pick("T03", r"^Basel-III \| Total$", "crar_b3"),
    pick("T03", r"^Basel-III \| Tier-I$", "tier1_b3"),
    pick("T11", r"21\. Return on assets$", "roa_rbi"),
    pick("T11", r"22\. Return on equity$", "roe_rbi"),
    pick("T11", r"Ratio of net NPA To net advances", "net_npa_ratio_rbi"),
    pick("T11", r"Capital adequacy ratio$", "crar_t11"),
    pick("T11", r"Ratio of intermediation cost to total assets", "intermediation_cost_ta_rbi"),
]
wide = pd.concat(series, axis=1).reset_index()
wide["bank_id"] = wide["rbi_name"].map(RBI_NAMES)
wide["group_id"] = wide["rbi_name"].map(RBI_GROUPS)

# CRAR: latest Basel regime available, else T11 ratio
wide["crar"] = wide["crar_b3"].combine_first(wide["crar_b2"]).combine_first(wide["crar_b1"]).combine_first(wide["crar_t11"])

# ---------- derived (same formulas for banks and group aggregates) ----------
def derive(d, key):
    d = d.sort_values([key, "fy"]).copy()
    d["equity"] = d["capital"] + d["reserves"]
    g = d.groupby(key)
    prev_fy_ok = g["fy"].shift(1) == d["fy"] - 1
    d["avg_equity"] = np.where(prev_fy_ok, (d["equity"] + g["equity"].shift(1)) / 2, np.nan)
    d["avg_assets"] = np.where(prev_fy_ok, (d["total_assets"] + g["total_assets"].shift(1)) / 2, np.nan)
    d["roe"] = d["pat"] / d["avg_equity"] * 100
    d["roa"] = d["pat"] / d["avg_assets"] * 100
    d["ln_assets"] = np.log(d["total_assets"])
    d["ldr"] = d["advances"] / d["deposits"] * 100
    d["liquid_assets"] = d[["cash", "bal_rbi", "bal_banks_india", "call_money", "bal_banks_abroad"]].sum(axis=1, min_count=5)
    d["liquidity_ratio"] = d["liquid_assets"] / d["total_assets"] * 100
    # Gross advances approximated as net advances + (gross NPA - net NPA), i.e. adding back NPA provisions.
    d["gross_advances"] = d["advances"] + d["gross_npa"] - d["net_npa"]
    d["gnpa_ratio"] = d["gross_npa"] / d["gross_advances"] * 100
    d["nnpa_ratio"] = d["net_npa"] / d["advances"] * 100
    d["cost_income"] = d["opex"] / (d["nii"] + d["other_income"]) * 100
    d["bs_gap"] = d["total_assets"] - d["total_liabilities_incl_equity"]
    return d


banks = derive(wide[wide["bank_id"].notna()].drop(columns="group_id"), "rbi_name")
# One row per bank_id x fy (IDFC Bank / IDFC First never overlap in FY)
assert not banks.duplicated(["bank_id", "fy"]).any(), "bank_id x fy not unique"
# Average equity/assets across the IDFC rename uses the same legal entity, so recompute on bank_id.
banks = derive(banks.drop(columns=[c for c in banks.columns if c in (
    "equity", "avg_equity", "avg_assets", "roe", "roa", "ln_assets", "ldr", "liquid_assets", "liquidity_ratio",
    "gross_advances", "gnpa_ratio", "nnpa_ratio", "cost_income", "bs_gap")]), "bank_id")
groups = derive(wide[wide["group_id"].notna()].drop(columns="bank_id"), "group_id")

meta = pd.DataFrame([(f[0], f[2]) for f in FIRMS if f[4]], columns=["bank_id", "bank_type"])
banks = banks.merge(meta, on="bank_id", how="left", validate="many_to_one")
lead = ["bank_id", "bank_type", "rbi_name", "fy"]
banks = banks[lead + [c for c in banks.columns if c not in lead]].sort_values(["bank_id", "fy"])
banks.to_csv(INTERIM / "rbi_bank_financials.csv", index=False)
groups = groups[["group_id", "rbi_name", "fy"] + [c for c in groups.columns if c not in ("group_id", "rbi_name", "fy")]]
groups.sort_values(["group_id", "fy"]).to_csv(INTERIM / "rbi_group_financials.csv", index=False)

# ---------- diagnostics ----------
print(f"\nbank-year rows: {len(banks)}  banks: {banks.bank_id.nunique()} / {len(meta)}")
missing_banks = sorted(set(meta.bank_id) - set(banks.bank_id))
print("panel banks with no RBI rows:", missing_banks or "none")
key = ["roe", "roa", "ln_assets", "crar", "ldr", "liquidity_ratio", "gnpa_ratio", "pat", "total_assets"]
p = banks[banks.fy.between(2010, 2025)]
cov = p.groupby("fy")[key].apply(lambda x: x.notna().sum())
print("\nnon-missing banks per FY (FY2010-25):")
print(cov.to_string())
print("\nbalance-sheet identity |assets - liabilities| > 1 crore:", (banks["bs_gap"].abs() > 1).sum())
chk = banks.dropna(subset=["roa", "roa_rbi"])
print(f"ROA vs RBI T11 ROA: corr={chk.roa.corr(chk.roa_rbi):.3f}, median |diff|={(chk.roa - chk.roa_rbi).abs().median():.3f} pp")
chk = banks.dropna(subset=["roe", "roe_rbi"])
print(f"ROE vs RBI T11 ROE: corr={chk.roe.corr(chk.roe_rbi):.3f}, median |diff|={(chk.roe - chk.roe_rbi).abs().median():.3f} pp")
print(f"CRAR (T03) vs T11: median |diff|={(banks.crar_b3 - banks.crar_t11).abs().median():.3f}")
print("\nNA cells (FY2011-25) by bank:")
na = banks[banks.fy.between(2011, 2025)].groupby("bank_id")[key].apply(lambda x: x.isna().sum())
print(na[na.sum(axis=1) > 0].to_string())
print("\ngroups:", groups.group_id.unique(), "FY", groups.fy.min(), "-", groups.fy.max())
