"""Download bank annual reports (PDF) from BSE corporate filings.

Usage: python 01_download_annual_reports.py [--index-only]
Writes data/raw/annual_reports/_index.csv (all BSE listings) and {bank_id}/FY{year}.pdf (one per bank-FY).
"""
import sys
import time
from datetime import date

import pandas as pd
import requests

from config import AR_FY, BSE_CODES, RAW

OUT = RAW / "annual_reports"
OUT.mkdir(parents=True, exist_ok=True)
API = "https://api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode={}"
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}

rows = []
for bank_id, code in BSE_CODES.items():
    r = requests.get(API.format(code), headers=H, timeout=60)
    r.raise_for_status()
    for t in r.json().get("Table", []):
        rows.append({"bank_id": bank_id, "scripcode": code, "scrip_name": t["scrip_name"].strip(),
                     "fy": int(t["Year"]), "status": t["status"], "url": t["PDFDownload"],
                     "authorised": t["Fld_AuthoriseDate"], "revised": t["revised_date_time"],
                     "resub_reason": (t["Fld_ResubReason"] or "").strip()})
    time.sleep(0.5)
idx = pd.DataFrame(rows)
idx["listed_on"] = date.today().isoformat()

print(idx.groupby(["bank_id", "scrip_name"]).fy.agg(["min", "max", "count"]).to_string())

# One report per bank-FY: latest full English filing. Resubmissions that are Hindi editions, errata or
# corrigenda are never selected (e.g. Union FY2024/25 "Hindi Version", Canara FY2023 "ERRATA").
idx["stamp"] = pd.to_datetime(idx["revised"].fillna(idx["authorised"]), errors="coerce")
idx["partial"] = idx["resub_reason"].fillna("").str.contains(r"hindi|errata|corrigendum", case=False)
idx["rank"] = (idx.assign(rev=(idx["status"] == "Revised").astype(int))
               .sort_values(["partial", "rev", "stamp"], ascending=[True, False, False])
               .groupby(["bank_id", "fy"]).cumcount())
idx["selected"] = (idx["rank"] == 0) & idx["fy"].between(*AR_FY)
# Files downloaded before .url sidecars existed followed the old rule (latest revised filing, else original).
old_rank = (idx.assign(rev=(idx["status"] == "Revised").astype(int)).sort_values(["rev", "stamp"], ascending=False)
            .groupby(["bank_id", "fy"]).cumcount())
old_url = idx[old_rank == 0].set_index(["bank_id", "fy"])["url"]
idx["file"] = idx.apply(lambda r: f"{r.bank_id}/FY{r.fy}.pdf" if r.selected else "", axis=1)
idx.drop(columns=["rank"]).to_csv(OUT / "_index.csv", index=False)
changed = idx[idx["selected"]].apply(lambda r: old_url.get((r.bank_id, r.fy)) != r.url, axis=1)
print("selection changed vs old rule:", idx[idx["selected"]][changed][["bank_id", "fy", "resub_reason"]].to_dict("records"))

sel = idx[idx["selected"]]
grid = sel.pivot_table(index="bank_id", columns="fy", values="url", aggfunc="count").reindex(index=list(BSE_CODES))
print("\nselected reports per bank x FY (1 = available on BSE):")
print(grid.fillna(0).astype(int).to_string())
print(f"\nselected: {len(sel)} of {len(BSE_CODES) * (AR_FY[1] - AR_FY[0] + 1)} bank-FY cells")

if "--index-only" in sys.argv:
    sys.exit(0)

s = requests.Session()
s.headers.update(H)
log = []
for r in sel.itertuples():
    path = OUT / r.file
    path.parent.mkdir(exist_ok=True)
    src = path.with_suffix(".url")
    prev = src.read_text().strip() if src.exists() else old_url.get((r.bank_id, r.fy))
    if path.exists() and path.stat().st_size > 10_000 and prev == r.url:
        src.write_text(r.url)
        log.append((r.bank_id, r.fy, "exists", path.stat().st_size)); continue
    for attempt in range(3):
        try:
            resp = s.get(r.url, timeout=300)
            ok = resp.status_code == 200 and resp.content[:4] == b"%PDF"
            if ok:
                path.write_bytes(resp.content)
                src.write_text(r.url)
                log.append((r.bank_id, r.fy, "ok", len(resp.content)))
                print(f"{r.bank_id:10s} FY{r.fy} {len(resp.content) / 1e6:6.1f} MB", flush=True)
                break
            status = f"bad:{resp.status_code}:{resp.content[:4]!r}"
        except requests.RequestException as e:
            status = f"error:{type(e).__name__}"
        time.sleep(3 * (attempt + 1))
    else:
        log.append((r.bank_id, r.fy, status, 0))
        print(f"{r.bank_id:10s} FY{r.fy} FAILED {status}", flush=True)
    time.sleep(1)

pd.DataFrame(log, columns=["bank_id", "fy", "status", "bytes"]).to_csv(OUT / "_download_log.csv", index=False)
print("done:", pd.Series([l[2].split(":")[0] for l in log]).value_counts().to_dict())
