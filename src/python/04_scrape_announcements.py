"""Collect BSE corporate announcements for the 14 event-study firms (2015 to today) and flag AI-related ones.

Stage 1 (cached, resume-safe): all announcements -> data/raw/bse_announcements/{firm_id}.csv
Stage 2: AI keyword match on subject/headline; for press/media-release-like filings also on the attachment text.
Output: data/interim/events_scraped.csv
If BSE blocks requests (non-200 / non-JSON), the script reports it and stops; it does not try to work around blocks.
"""
import sys
import time
from datetime import date

import pandas as pd
import pymupdf
import requests

from ai_terms import count_terms, normalise
from config import BSE_CODES, BSE_CODES_EVENT_NONBANK, FIRMS, INTERIM, RAW

START = date(2015, 1, 1)
SLEEP = 0.7
OUT = RAW / "bse_announcements"
PDF = OUT / "pdf"
PDF.mkdir(parents=True, exist_ok=True)
API = ("https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno={page}&strCat=-1"
       "&strPrevDate={frm}&strScrip={code}&strSearch=P&strToDate={to}&strType=C&subcategory=-1")
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}
KEEP = ["NEWSID", "SCRIP_CD", "SLONGNAME", "NEWSSUB", "HEADLINE", "MORE", "CATEGORYNAME", "SUBCATNAME",
        "NEWS_DT", "DissemDT", "ATTACHMENTNAME", "Fld_Attachsize"]

event_firms = [f[0] for f in FIRMS if f[5]]
codes = {**BSE_CODES, **BSE_CODES_EVENT_NONBANK}
names = {f[0]: f[1] for f in FIRMS}
s = requests.Session()
s.headers.update(H)


class Blocked(Exception):
    pass


def get_json(url):
    # Transient 400/5xx/timeouts are retried with backoff; 401/403/429 are treated as a block and stop the run.
    for attempt in range(4):
        try:
            r = s.get(url, timeout=60)
        except requests.RequestException:
            time.sleep(10 * (attempt + 1)); continue
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            return r.json()
        if r.status_code in (401, 403, 429):
            break
        time.sleep(10 * (attempt + 1))
    raise Blocked(f"HTTP {r.status_code} {r.headers.get('content-type')} for {url}")


def fetch_firm(fid):
    path = OUT / f"{fid}.csv"
    if path.exists():
        return pd.read_csv(path, dtype=str)
    rows = []
    windows = pd.date_range(START, date.today(), freq="QS").tolist() + [pd.Timestamp(date.today()) + pd.Timedelta(days=1)]
    for a, b in zip(windows[:-1], windows[1:]):
        frm, to = a.strftime("%Y%m%d"), (b - pd.Timedelta(days=1)).strftime("%Y%m%d")
        page = 1
        while True:
            j = get_json(API.format(page=page, frm=frm, to=to, code=codes[fid]))
            t = j.get("Table", [])
            rows += [{k: x.get(k) for k in KEEP} for x in t]
            total = int((j.get("Table1") or [{"ROWCNT": 0}])[0]["ROWCNT"])
            time.sleep(SLEEP)
            if page * 50 >= total or not t:
                break
            page += 1
    df = pd.DataFrame(rows, columns=KEEP).drop_duplicates("NEWSID")
    df.insert(0, "firm_id", fid)
    df.to_csv(path, index=False)
    return df.astype(str)


# ---------- stage 1 ----------
frames = []
try:
    for fid in event_firms:
        df = fetch_firm(fid)
        print(f"{fid:10s} {codes[fid]} {df['SLONGNAME'].iloc[0] if len(df) else '':40s} announcements={len(df)}", flush=True)
        frames.append(df)
except Blocked as e:
    sys.exit(f"STOPPED: BSE blocked the request ({e}). Not attempting to bypass.")
ann = pd.concat(frames, ignore_index=True)
ann.to_csv(OUT / "_all.csv", index=False)
with open(OUT / "_fetched_on.txt", "w") as f:
    f.write(date.today().isoformat())

# ---------- stage 2 ----------
ann = ann.fillna("")
ann["text"] = (ann["NEWSSUB"] + " | " + ann["HEADLINE"] + " | " + ann["MORE"]).map(normalise)
subj_counts = ann["text"].map(count_terms)
ann["subj_terms"] = subj_counts.map(lambda c: ",".join(k for k, v in c.items() if v))

release_like = (
    ann["SUBCATNAME"].str.contains(r"Press Release|Media Release", case=False)
    | ann["CATEGORYNAME"].str.contains(r"Press Release|Media Release", case=False)
    | ann["text"].str.contains(r"press release|media release|launch|partner|tie[\s-]?up|collaborat|\bMoU\b|"
                               r"memorandum of understanding|introduc|unveil|invest(?:s|ment) in|acqui", case=False)
)
skip = ann["text"].str.contains(r"financial results|board meeting|trading window|allotment|shareholding pattern|"
                                r"credit rating|loss of share certificate|record date|AGM|postal ballot", case=False)
scan = ann[release_like & ~skip & (ann["ATTACHMENTNAME"] != "") & (ann["subj_terms"] == "")]
print(f"\nsubject/headline AI matches: {(ann.subj_terms != '').sum()}; attachments to scan: {len(scan)}", flush=True)

att_terms = {}
for i, r in enumerate(scan.itertuples()):
    pdf = PDF / r.ATTACHMENTNAME
    if not pdf.exists():
        got = None
        for folder in ("AttachHis", "AttachLive"):
            resp = s.get(f"https://www.bseindia.com/xml-data/corpfiling/{folder}/{r.ATTACHMENTNAME}", timeout=120)
            time.sleep(SLEEP)
            if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                got = resp.content
                break
            if resp.status_code in (401, 403, 429):
                sys.exit(f"STOPPED: BSE blocked attachment download (HTTP {resp.status_code}). Not bypassing.")
        if got is None:
            continue
        pdf.write_bytes(got)
    try:
        with pymupdf.open(pdf) as doc:
            txt = normalise(" ".join(p.get_text("text") for p in list(doc)[:6]))
    except Exception:
        continue
    c = count_terms(txt)
    att_terms[r.NEWSID] = ",".join(f"{k}:{v}" for k, v in c.items() if v)
    if i % 100 == 0:
        print(f"  scanned {i}/{len(scan)}", flush=True)
ann["attach_terms"] = ann["NEWSID"].map(att_terms).fillna("")
ann["attach_scanned"] = ann["NEWSID"].isin(scan["NEWSID"])

hits = ann[(ann["subj_terms"] != "") | (ann["attach_terms"] != "")].copy()
dt = pd.to_datetime(hits["DissemDT"].where(hits["DissemDT"] != "", hits["NEWS_DT"]), format="ISO8601")
assert dt.notna().all()
hits["date"] = dt.dt.strftime("%Y-%m-%d")
hits["time_ist"] = dt.dt.strftime("%H:%M")
hits["company"] = hits["firm_id"].map(names)
hits["match_source"] = hits.apply(lambda r: "subject" if r.subj_terms else "attachment", axis=1)
folder = (dt < pd.Timestamp(date.today()) - pd.Timedelta(days=7)).map({True: "AttachHis", False: "AttachLive"})
hits["link"] = "https://www.bseindia.com/xml-data/corpfiling/" + folder + "/" + hits["ATTACHMENTNAME"]

# Duplicates of candidate events: same firm, date within +/-3 calendar days
ev = pd.read_csv(RAW / "events.csv", dtype=str)
from config import EVENT_COMPANIES  # noqa: E402
ev["firm_id"] = ev["company"].map(EVENT_COMPANIES)
ev["d"] = pd.to_datetime(ev["event_date"], format="%Y-%m-%d", errors="coerce")
dup = []
for r in hits.itertuples():
    m = ev[(ev.firm_id == r.firm_id) & ((ev.d - pd.Timestamp(r.date)).abs() <= pd.Timedelta(days=3))]
    dup.append(",".join(m.event_id))
hits["duplicate_of"] = dup
hits["is_duplicate"] = (hits["duplicate_of"] != "").map({True: "Y", False: "N"})

cols = ["firm_id", "company", "date", "time_ist", "CATEGORYNAME", "SUBCATNAME", "NEWSSUB", "HEADLINE",
        "match_source", "subj_terms", "attach_terms", "is_duplicate", "duplicate_of", "link", "NEWSID"]
hits = hits[cols].rename(columns={"NEWSSUB": "subject", "HEADLINE": "headline", "CATEGORYNAME": "category",
                                  "SUBCATNAME": "subcategory"}).sort_values(["firm_id", "date"])
hits.to_csv(INTERIM / "events_scraped.csv", index=False)

print(f"\nannouncements: {len(ann):,}  AI matches: {len(hits)}  (subject {(hits.match_source == 'subject').sum()}, "
      f"attachment {(hits.match_source == 'attachment').sum()})  duplicates of candidates: {(hits.is_duplicate == 'Y').sum()}")
print(hits.groupby("firm_id").size().to_string())
