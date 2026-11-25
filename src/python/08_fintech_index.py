"""Fintech index (proxy 5; Hamdouni 2025): equal-weighted mean (1/6 each) of
  (a) bank-wise mobile-banking transaction volume (RBI monthly releases), FY total, min-max scaled 0-1 over all
      bank-FYs; FY volume annualised from >= 6 months (mean monthly x 12), else NA;
  (b) feature dummies mobile_app, upi, chatbot, voice_assistant, video_kyc = 1 from the first FY the bank's annual
      report mentions the feature (absorbing). NA index where (a) is NA.
Step 1 downloads RBI pages (cached, resume-safe) - long; step 2 parses. Summary <= 20 lines; details logs/fintech.log.
"""
import io
import re
import time

import numpy as np
import pandas as pd
import requests

from config import FIRMS, INTERIM, RAW

OUT = RAW / "mobile_banking" / "html"
OUT.mkdir(parents=True, exist_ok=True)
LOG = RAW.parent.parent / "logs" / "fintech.log"
LOG.parent.mkdir(exist_ok=True)
log = open(LOG, "w", encoding="utf-8")
URL = "https://rbi.org.in/scripts/NEFTUserView.aspx?Id={}"
PANEL = [f[0] for f in FIRMS if f[4]]
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
# RBI bank-name patterns -> panel bank_id (case-insensitive; checked against the parsed names in the log)
NAME_PAT = {
    "SBI": r"^state bank of india", "BOB": r"^bank of baroda", "PNB": r"^punjab national bank", "CANARA": r"^canara bank",
    "UNION": r"^union bank of india", "BOI": r"^bank of india", "INDIAN": r"^indian bank", "CENTRAL": r"^central bank of india",
    "IOB": r"^indian overseas bank", "UCO": r"^uco bank", "BOM": r"^bank of maharashtra", "PSB": r"^punjab (and|&) sind",
    "HDFC": r"^hdfc bank", "ICICI": r"^icici bank", "AXIS": r"^axis bank", "KOTAK": r"^kotak mahindra bank",
    "INDUSIND": r"^indusind bank", "FEDERAL": r"^(the )?federal bank", "YES": r"^yes bank", "RBL": r"^(rbl bank|ratnakar bank)",
    "KVB": r"^(the )?karur vysya", "CUB": r"^city union bank", "SIB": r"^(the )?south indian bank", "DCB": r"^(dcb bank|development credit bank)",
    "IDFCFIRST": r"^idfc (first )?bank"}

# ---- step 1: download (cached) ----
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0"})
i, empty_run = 1, 0
while not (i > 200 and empty_run >= 10) and i < 400:  # releases run ~Id 1 (2009) to ~Id 220 (2026)
    f = OUT / f"{i}.html"
    if not f.exists():
        for attempt in range(3):
            try:
                r = s.get(URL.format(i), timeout=90)
                break
            except requests.RequestException:
                time.sleep(10 * (attempt + 1))
        else:
            r = None
        if r is None or r.status_code != 200:
            print(f"Id {i}: failed", file=log); i += 1; empty_run += 1; continue
        f.write_text(r.text, encoding="utf-8")
        time.sleep(0.5)
    has = "Bank-wise" in f.read_text(encoding="utf-8", errors="ignore")
    empty_run = 0 if has else empty_run + 1
    i += 1

# ---- step 2: parse mobile-banking tables ----
rows = []
for f in sorted(OUT.glob("*.html"), key=lambda x: int(x.stem)):
    t = f.read_text(encoding="utf-8", errors="ignore")
    if "Mobile Banking" not in t:
        continue
    try:
        tabs = pd.read_html(io.StringIO(t))
    except ValueError:
        continue
    for tab in tabs:
        head = str(tab.iloc[0, 0])  # the page is wrapped in an outer layout table; use only tables titled in cell (0,0)
        m = re.match(r"\s*Bank[\s-]*wise Mobile Banking.*?month of\s+([A-Za-z]+),?\s+(\d{4})", head, re.I)
        if not m or m.group(1).lower() not in MONTHS:
            continue
        mon, yr = MONTHS[m.group(1).lower()], int(m.group(2))
        hdr = next((k for k in range(min(5, len(tab))) if any("bank name" in str(v).lower() for v in tab.iloc[k])), None)
        if hdr is None:
            continue
        cols = [str(v).lower() for v in tab.iloc[hdr]]
        ib = next(k for k, c in enumerate(cols) if "bank name" in c)
        iv = next((k for k, c in enumerate(cols) if "volume" in c), None)
        if iv is None:
            continue
        for _, rr in tab.iloc[hdr + 1:].iterrows():
            name = str(rr.iloc[ib]).strip()
            vol = pd.to_numeric(str(rr.iloc[iv]).replace(",", ""), errors="coerce")
            bid = next((b for b, p in NAME_PAT.items() if re.search(p, name, re.I)), None)
            if bid:
                rows.append({"bank_id": bid, "rbi_name": name, "year": yr, "month": mon, "volume": vol, "page_id": int(f.stem)})
        break
mb = pd.DataFrame(rows).drop_duplicates(["bank_id", "year", "month", "rbi_name"])
# several RBI names can map to one bank (e.g. old/new names); sum within bank-month, keep the latest page if duplicated
mb = mb.sort_values("page_id").drop_duplicates(["bank_id", "year", "month", "rbi_name"], keep="last")
mm = mb.groupby(["bank_id", "year", "month"])["volume"].sum(min_count=1).reset_index()
mm["fy"] = mm["year"] + (mm["month"] >= 4).astype(int)
fyv = mm.groupby(["bank_id", "fy"]).agg(n_months=("volume", "count"), vol_mean=("volume", "mean")).reset_index()
fyv["mb_volume_fy"] = np.where(fyv["n_months"] >= 6, fyv["vol_mean"] * 12, np.nan)
print(mb.groupby("bank_id")["rbi_name"].unique().to_string(), file=log)

# ---- feature dummies from annual-report first mentions ----
FEAT = {"mobile_app": r"(?i)mobile\s+(?:banking\s+)?(?:app|application)\b|\bm-?banking app",
        "upi": r"\bUPI\b|(?i:unified payments? interface)",
        "chatbot": r"(?i)\bchat[\s-]?bots?\b|virtual assistant",
        "voice_assistant": r"(?i)voice\s*(?:bot|assistant|banking)|\balexa\b|google assistant",
        "video_kyc": r"(?i)video[\s-]*(?:based\s+)?kyc|\bv-?cip\b|video customer identification"}
kwf = pd.read_csv(INTERIM / "ai_kw.csv", usecols=["bank_id", "fy"])
feat = []
for r in kwf.itertuples():
    p = INTERIM / "ar_text" / f"{r.bank_id}_FY{r.fy}.txt"
    t = p.read_text(encoding="utf-8").split("\n", 1)[1] if p.exists() else ""
    feat.append({"bank_id": r.bank_id, "fy": r.fy, **{k: int(bool(re.search(v, t))) for k, v in FEAT.items()}})
feat = pd.DataFrame(feat)
grid = pd.MultiIndex.from_product([PANEL, range(2011, 2027)], names=["bank_id", "fy"]).to_frame(index=False)
grid = grid.merge(feat, on=["bank_id", "fy"], how="left").sort_values(["bank_id", "fy"])
for k in FEAT:  # absorbing: 1 from first mention onward; 0 before
    grid[k] = grid.groupby("bank_id")[k].transform(lambda x: x.fillna(0).cummax()).astype(int)

fi = grid.merge(fyv[["bank_id", "fy", "n_months", "mb_volume_fy"]], on=["bank_id", "fy"], how="left", validate="one_to_one")
lo, hi = fi["mb_volume_fy"].min(), fi["mb_volume_fy"].max()
fi["mb_volume_scaled"] = (fi["mb_volume_fy"] - lo) / (hi - lo)
items = ["mb_volume_scaled"] + list(FEAT)
fi["fintech_idx"] = np.where(fi["mb_volume_scaled"].notna(), fi[items].mean(axis=1), np.nan)
assert not fi.duplicated(["bank_id", "fy"]).any()
fi.to_csv(INTERIM / "fintech_idx.csv", index=False)

cov = fi.groupby("fy").agg(banks_with_volume=("mb_volume_fy", "count"), fintech_idx_n=("fintech_idx", "count"),
                           mean_idx=("fintech_idx", "mean"))
print(f"RBI pages cached: {len(list(OUT.glob('*.html')))}; bank-months parsed: {len(mm)}; months {mm.year.min()}-{mm.year.max()}")
print(cov.round(3).to_string())
print(f"first FY with feature (banks): " + ", ".join(f"{k} {int(fi[fi[k] == 1].groupby('bank_id').fy.min().median())}" for k in FEAT))
print(f"details: {LOG}")
