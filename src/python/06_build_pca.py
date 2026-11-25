"""RBI Prompt Corrective Action (PCA) spells for panel banks -> bank x FY pca_months and pca.

Sources (fetched with requests; no browser):
  exits   : RBI press releases (rbi.org.in BS_PressReleaseDisplay.aspx?prid=...)
  entries : the bank's own BSE filing quoting RBI's letter (BSE announcements API, 2015-2018)
  check   : PIB release of March 2018 listing PSBs under PCA
Coding: pca_months = FY months (Apr-Mar) with >= 15 days under PCA; pca = 1 if pca_months >= 6.
Summary <= 20 lines to stdout; details to logs/pca.log.
"""
import re
import time
from datetime import date

import pandas as pd
import pymupdf
import requests

from ai_terms import normalise
from config import BSE_CODES, INTERIM, RAW

ROOT = RAW.parent.parent
LOG = ROOT / "logs" / "pca.log"
LOG.parent.mkdir(exist_ok=True)
OUT = RAW / "pca"
(OUT / "pdf").mkdir(parents=True, exist_ok=True)
BANKS = ["BOI", "BOM", "UCO", "IOB", "CENTRAL"]
NAMES = {"BOI": "Bank of India", "BOM": "Bank of Maharashtra", "UCO": "UCO Bank",
         "IOB": "Indian Overseas Bank", "CENTRAL": "Central Bank of India"}
RBI_PRIDS = [46165, 52198, 52318, 54395]  # 2019-01-31 BOI/BOM/OBC; 2021-09-08 UCO; 2021-09-29 IOB; 2022-09-20 Central
PIB_URL = "https://www.pib.gov.in/newsite/PrintRelease.aspx?relid=177591"
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}
API = ("https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno={page}&strCat=-1&strPrevDate={frm}"
       "&strScrip={code}&strSearch=P&strToDate={to}&strType=C&subcategory=-1")
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
log = open(LOG, "w", encoding="utf-8")


def say(*a):
    print(*a, file=log, flush=True)


def html_text(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
    return r.status_code, re.sub(r"\s+", " ", re.sub(r"&nbsp;|&#160;", " ", re.sub(r"<[^>]+>", " ", t)))


def has_bank(b, text):
    """Name match that does not count 'Bank of India' inside 'Central Bank of India'."""
    return re.search(rf"(?<!Central )\b{re.escape(NAMES[b])}\b", text, re.I) is not None


def parse_date(s):
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %B %Y", "%d %B, %Y", "%B %d %Y"):
        try:
            return pd.Timestamp(pd.to_datetime(re.sub(r"(\d)(st|nd|rd|th)", r"\1", s.strip()), format=fmt))
        except ValueError:
            pass
    try:
        return pd.Timestamp(pd.to_datetime(s.strip(), dayfirst=True))
    except (ValueError, TypeError):
        return pd.NaT


# ---- exits: RBI press releases ----
exits = {}
for prid in RBI_PRIDS:
    url = f"https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid={prid}"
    code, t = html_text(url)
    m = re.search(r"Date\s*:\s*([A-Za-z]{3}\s*\d{1,2},\s*\d{4})", t)
    k = t.find("Prompt Corrective")
    body = t[k: k + 1500] if k >= 0 else ""
    say(f"RBI prid={prid} HTTP {code} date={m.group(1) if m else None} | {body[:300]}")
    if not m or k < 0:
        continue
    for b in BANKS:
        if has_bank(b, body) and re.search(r"taken out|removed|exit", body, re.I):
            exits[b] = (parse_date(m.group(1)), url)
    time.sleep(1)

# ---- PIB cross-check ----
code, pib = html_text(PIB_URL)
pm = re.search(rf"(\d{{1,2}}[- ](?:{MONTHS}|[A-Z][a-z]{{2}})[- ]\d{{4}})", pib)
pib_date = parse_date(pm.group(1).replace("-", " ")) if pm else pd.NaT
k = pib.find("eleven")
say(f"PIB HTTP {code} date={pib_date} | {pib[max(k - 200, 0): k + 600]}")
pib_banks = {b for b in BANKS if has_bank(b, pib)}

# ---- entries: bank BSE filings mentioning PCA, 2015-2018 ----
s = requests.Session()
s.headers.update(H)


def get(url, timeout=60):
    """Retry timeouts / transient errors; a 401/403/429 is returned as-is (treated as blocked, not bypassed)."""
    for attempt in range(4):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code in (200, 401, 403, 404, 429):
                return r
        except requests.RequestException:
            pass
        time.sleep(10 * (attempt + 1))
    return s.get(url, timeout=timeout)


rows = []
cached = OUT / "bse_pca_filings.csv"
for b in ([] if cached.exists() else BANKS):  # delete the cache file to re-query BSE
    for a in pd.date_range("2015-01-01", "2018-12-31", freq="QS"):
        frm, to = a.strftime("%Y%m%d"), (a + pd.offsets.QuarterEnd(0)).strftime("%Y%m%d")
        page = 1
        while True:
            r = get(API.format(page=page, frm=frm, to=to, code=BSE_CODES[b]))
            if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                say(f"BSE blocked/failed {b} {frm} HTTP {r.status_code}")
                break
            j = r.json()
            t = j.get("Table", [])
            for x in t:
                txt = f"{x.get('NEWSSUB', '')} {x.get('HEADLINE', '')} {x.get('MORE', '')}"
                if re.search(r"prompt\s+corrective|\bPCA\b", txt, re.I):
                    rows.append({"bank_id": b, "dissem": x.get("DissemDT") or x.get("NEWS_DT"),
                                 "subject": x.get("NEWSSUB", ""), "headline": (x.get("HEADLINE") or "")[:300],
                                 "attachment": x.get("ATTACHMENTNAME", "")})
            time.sleep(0.7)
            total = int((j.get("Table1") or [{"ROWCNT": 0}])[0]["ROWCNT"])
            if page * 50 >= total or not t:
                break
            page += 1
if cached.exists():
    filings = pd.read_csv(cached, dtype=str).fillna("")
else:
    filings = pd.DataFrame(rows)
    filings.to_csv(cached, index=False)

# For each bank, the earliest PCA filing: read RBI letter date from headline or attachment text
entries = {}
for b in BANKS:
    f = filings[filings.bank_id == b].sort_values("dissem") if len(filings) else filings
    for r in f.itertuples():
        text = r.headline
        pdf = OUT / "pdf" / r.attachment
        if r.attachment and not pdf.exists():
            for folder in ("AttachHis", "AttachLive"):
                resp = get(f"https://www.bseindia.com/xml-data/corpfiling/{folder}/{r.attachment}", timeout=120)
                time.sleep(1)
                if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                    pdf.write_bytes(resp.content)
                    break
        if r.attachment and pdf.is_file():
            with pymupdf.open(pdf) as d:
                text += " " + normalise(" ".join(p.get_text("text") for p in list(d)[:3]))
        m = re.search(rf"letter\s+(?:no\.?\s*[\w./-]*\s*)?dated\s+((?:\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS}),?\s+\d{{4}})"
                      rf"|(?:(?:{MONTHS})\s+\d{{1,2}},?\s+\d{{4}})|\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{4}})", text, re.I)
        say(f"{b} filing {r.dissem} | {r.subject[:120]} | letter: {m.group(1) if m else None} | {text[:400]}")
        src = (f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{r.attachment}" if r.attachment
               else f"BSE announcement {r.dissem[:16]} ({r.subject})")
        placed = re.search(r"(initiat|placed|impos|invok|put)\w*.{0,60}prompt corrective|prompt corrective.{0,60}"
                           r"(initiat|placed|impos|invok)", text, re.I)
        if placed and b not in entries:
            if m:
                entries[b] = (parse_date(m.group(1)), pd.Timestamp(r.dissem[:10]), src, "RBI letter date quoted in filing")
            else:  # bank's own filing announces PCA but gives no letter date: use the filing date
                entries[b] = (pd.Timestamp(r.dissem[:10]), pd.Timestamp(r.dissem[:10]), src,
                              "filing date (letter date not stated)")

# ---- spells ----
sp = []
for b in BANKS:
    if b in entries:
        ent, filed, src, basis = entries[b]
        inferred = 0
    else:
        ent, filed, src, inferred, basis = pib_date, pd.NaT, PIB_URL, 1, "on or before PIB release (no filing found)"
    ex, ex_src = exits.get(b, (pd.NaT, ""))
    sp.append({"bank_id": b, "entry_date": ent, "entry_basis": basis, "entry_filing_date": filed, "entry_source": src,
               "entry_inferred": inferred, "in_pib_2018": int(b in pib_banks), "exit_date": ex, "exit_source": ex_src})
sp = pd.DataFrame(sp)
for c in ["entry_date", "entry_filing_date", "exit_date"]:
    sp[c] = pd.to_datetime(sp[c]).dt.strftime("%Y-%m-%d")
sp.to_csv(INTERIM / "pca_spells.csv", index=False)

# ---- bank x FY months ----
fy_rows = []
for r in sp.itertuples():
    start = pd.Timestamp(r.entry_date) if isinstance(r.entry_date, str) else None
    end = pd.Timestamp(r.exit_date) - pd.Timedelta(days=1) if isinstance(r.exit_date, str) else pd.Timestamp(date.today())
    for fy in range(2011, 2027):
        months = 0
        for m in pd.date_range(f"{fy - 1}-04-01", f"{fy}-03-01", freq="MS"):
            me = m + pd.offsets.MonthEnd(0)
            if start is not None:
                overlap = (min(me, end) - max(m, start)).days + 1
                months += int(overlap >= 15)
        fy_rows.append({"bank_id": r.bank_id, "fy": fy, "pca_months": months, "pca": int(months >= 6)})
fy = pd.DataFrame(fy_rows)
assert not fy.duplicated(["bank_id", "fy"]).any()
fy.to_csv(INTERIM / "pca_bank_fy.csv", index=False)

print(f"PCA filings found on BSE (2015-18): {len(filings)}; PIB release date {pib_date.date() if pd.notna(pib_date) else None}")
print(sp[["bank_id", "entry_date", "entry_inferred", "in_pib_2018", "exit_date"]].to_string(index=False))
print("pca = 1 bank-FYs:", fy[fy.pca == 1].groupby("bank_id")["fy"].apply(lambda x: f"FY{x.min()}-FY{x.max()} ({len(x)})").to_dict())
print(f"details: {LOG}")
