"""ai_calls: AI-term count per 10,000 words in earnings-call transcripts filed on BSE, panel banks, FY2022 onward.

Long job (downloads PDFs): run yourself. Resume-safe (cached announcement lists and PDFs in data/raw/transcripts/).
Output data/interim/ai_calls.csv (bank_id x FY: n_transcripts, words, ai_count, ai_calls). Summary <= 20 lines;
details in logs/transcripts.log. If BSE answers 401/403/429 the script stops (no bypassing).
"""
import sys
import time

import pandas as pd
import pymupdf
import requests

from ai_terms import WORD, count_terms, normalise
from config import BSE_CODES, INTERIM, RAW

OUT = RAW / "transcripts"
(OUT / "pdf").mkdir(parents=True, exist_ok=True)
LOG = RAW.parent.parent / "logs" / "transcripts.log"
LOG.parent.mkdir(exist_ok=True)
log = open(LOG, "w", encoding="utf-8")
API = ("https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno={page}&strCat=-1&strPrevDate={frm}"
       "&strScrip={code}&strSearch=P&strToDate={to}&strType=C&subcategory=-1")
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"})


def get(url, timeout=60):
    for attempt in range(4):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code in (401, 403, 429):
                sys.exit(f"STOPPED: BSE returned {r.status_code} for {url} (not bypassing)")
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(10 * (attempt + 1))
    return None


rows = []
for b, code in BSE_CODES.items():
    cache = OUT / f"{b}_list.csv"
    if cache.exists():
        lst = pd.read_csv(cache, dtype=str).fillna("")
    else:
        hits, complete = [], True
        for a in pd.date_range("2021-04-01", pd.Timestamp.today(), freq="QS"):
            frm, to = a.strftime("%Y%m%d"), (a + pd.offsets.QuarterEnd(0)).strftime("%Y%m%d")
            page = 1
            while True:
                j = None
                for attempt in range(3):  # BSE sometimes answers 200 with an HTML/empty body
                    r = get(API.format(page=page, frm=frm, to=to, code=code))
                    try:
                        j = r.json() if r is not None else None
                        break
                    except ValueError:
                        time.sleep(20 * (attempt + 1))
                if j is None:
                    complete = False
                    print(f"{b} list incomplete: {frm}-{to} page {page}", file=log, flush=True)
                    break
                t = j.get("Table", [])
                hits += [x for x in t if "transcript" in f"{x.get('NEWSSUB', '')} {x.get('HEADLINE', '')}".lower()]
                total = int((j.get("Table1") or [{"ROWCNT": 0}])[0]["ROWCNT"])
                time.sleep(0.7)
                if page * 50 >= total or not t:
                    break
                page += 1
        lst = pd.DataFrame([{"dissem": x.get("DissemDT") or x.get("NEWS_DT"), "subject": x.get("NEWSSUB", ""),
                             "attachment": x.get("ATTACHMENTNAME", "")} for x in hits])
        if complete:  # an incomplete list is used this run but not cached, so a re-run fetches it again
            lst.to_csv(cache, index=False)
    for r in lst.itertuples():
        if not r.attachment:
            continue
        pdf = OUT / "pdf" / r.attachment
        if not pdf.is_file():
            for folder in ("AttachHis", "AttachLive"):
                resp = get(f"https://www.bseindia.com/xml-data/corpfiling/{folder}/{r.attachment}", timeout=180)
                time.sleep(1)
                if resp is not None and resp.content[:4] == b"%PDF":
                    pdf.write_bytes(resp.content)
                    break
        if not pdf.is_file():
            print(f"{b} missing PDF {r.attachment}", file=log)
            continue
        try:
            with pymupdf.open(pdf) as d:
                text = normalise(" ".join(p.get_text("text") for p in d))
        except Exception as e:
            print(f"{b} unreadable {r.attachment}: {e}", file=log)
            continue
        dt = pd.Timestamp(str(r.dissem)[:10])
        rows.append({"bank_id": b, "date": dt.date(), "fy": dt.year + (dt.month >= 4), "words": len(WORD.findall(text)),
                     "ai_count": sum(count_terms(text).values()), "attachment": r.attachment})
    print(f"{b}: {len(lst)} transcript filings", file=log, flush=True)

t = pd.DataFrame(rows)
t.to_csv(OUT / "transcripts_counts.csv", index=False)
fy = t.groupby(["bank_id", "fy"]).agg(n_transcripts=("words", "size"), words=("words", "sum"),
                                       ai_count=("ai_count", "sum")).reset_index()
fy["ai_calls"] = fy["ai_count"] / fy["words"] * 10_000
fy = fy[fy["fy"] >= 2022]
fy.to_csv(INTERIM / "ai_calls.csv", index=False)
print(f"transcripts parsed: {len(t)}; bank-FYs: {len(fy)}; banks: {fy.bank_id.nunique()} of {len(BSE_CODES)}")
print(fy.pivot(index="bank_id", columns="fy", values="n_transcripts").fillna(0).astype(int).to_string())
print(f"details: {LOG}")
