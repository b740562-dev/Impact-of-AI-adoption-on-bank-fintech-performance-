"""Quarterly results announcement dates for the 14 event-study firms, from BSE filings.

Input: data/raw/bse_announcements/_all.csv (written by 04_scrape_announcements.py)
Output: data/interim/earnings_dates.csv (one row per firm x results announcement)
earnings_within_3d for events is computed in 02_clean_events.py (data/raw/events.csv is never edited).
"""
import numpy as np
import pandas as pd

from config import INTERIM, RAW

CLUSTER_DAYS = 5  # filings of one results release (standalone, consolidated, press release, deck) within 5 days
CUTOFF = "15:30"

ann = pd.read_csv(RAW / "bse_announcements" / "_all.csv", dtype=str).fillna("")
subj = ann["NEWSSUB"].str.lower()
cat = ann["CATEGORYNAME"].str.strip().str.lower()
NOT_RESULTS = (r"related party|newspaper|publication|advertisement|monitoring agency|statement of deviation|"
               r"investor presentation|reg(?:ulation)?\.?\s*33\s*\(3\)|submission of quarterly|earnings call|"
               r"conference call|audio recording|transcript|analyst|investor meet")
NOTICE = r"intimation|to consider|will be held|is scheduled|prior notice|trading window|board meeting on"
# A: filings BSE files under 'Result' (headlines often carry boilerplate like "intimation attached")
a = (cat == "result") & ~subj.str.contains(NOT_RESULTS)
# B: results filed under other categories, identified from the subject line
b = (subj.str.contains(r"financial results?\b|audited results|unaudited results|results for the (?:quarter|year)")
     & ~subj.str.contains(NOT_RESULTS) & ~subj.str.contains(NOTICE))
# C (fallback only): board-meeting outcomes in results months, for quarters with no A/B filing
dts = pd.to_datetime(ann["DissemDT"].where(ann["DissemDT"] != "", ann["NEWS_DT"]), format="ISO8601")
c = ((ann["SUBCATNAME"].str.strip().str.lower() == "outcome of board meeting")
     & dts.dt.month.isin([1, 2, 4, 5, 7, 8, 10, 11]) & ~subj.str.contains(NOT_RESULTS))
ann["source"] = np.select([a, b, c], ["result_category", "result_subject", "board_outcome_fallback"], "")
res = ann[ann["source"] != ""].copy()
res["dt"] = pd.to_datetime(res["DissemDT"].where(res["DissemDT"] != "", res["NEWS_DT"]), format="ISO8601")
assert res["dt"].notna().all()
res = res.sort_values(["firm_id", "dt"])
mm, yy = res["dt"].dt.month, res["dt"].dt.year
res["fq"] = yy.where(mm <= 6, yy + 1).astype(str) + "-" + ((mm - 4) % 12 // 3 + 1).astype(str)
has_main = res[res["source"] != "board_outcome_fallback"].groupby("firm_id")["fq"].agg(set)
res = res[(res["source"] != "board_outcome_fallback")
          | ~res.apply(lambda r: r.fq in has_main.get(r.firm_id, set()), axis=1)]

rows = []
for fid, g in res.groupby("firm_id"):
    start = None
    for r in g.itertuples():
        if start is None or (r.dt - start["dt"]).days > CLUSTER_DAYS:
            if start is not None:
                rows.append(start)
            start = {"firm_id": fid, "dt": r.dt, "n_filings": 0, "first_subject": r.NEWSSUB, "source": r.source}
        start["n_filings"] += 1
    rows.append(start)
ed = pd.DataFrame(rows)
ed["results_date"] = ed["dt"].dt.strftime("%Y-%m-%d")
ed["results_time_ist"] = ed["dt"].dt.strftime("%H:%M")
ed["after_close"] = (ed["results_time_ist"] > CUTOFF).map({True: "Y", False: "N"})
# Quarter reported: results in Apr-Jun -> Q4 of FY ending that March; Jul-Sep -> Q1; Oct-Dec -> Q2; Jan-Mar -> Q3
m, y = ed["dt"].dt.month, ed["dt"].dt.year
ed["fy_reported"] = y.where(m <= 6, y + 1)
ed["quarter_reported"] = m.map(lambda k: "Q4" if 4 <= k <= 6 else "Q1" if 7 <= k <= 9 else "Q2" if k >= 10 else "Q3")
ed = ed[["firm_id", "results_date", "results_time_ist", "after_close", "fy_reported", "quarter_reported",
         "n_filings", "source", "first_subject"]]
n_clusters = len(ed)
# The results announcement is the first results filing for the quarter; later clusters are refilings.
ed = ed.sort_values(["firm_id", "results_date"]).drop_duplicates(["firm_id", "fy_reported", "quarter_reported"])
print(f"clusters: {n_clusters} -> first per firm-quarter: {len(ed)}")
assert not ed.duplicated(["firm_id", "results_date"]).any()
ed.to_csv(INTERIM / "earnings_dates.csv", index=False)

print(f"results announcements: {len(ed)} for {ed.firm_id.nunique()} firms")
cnt = ed.pivot_table(index="firm_id", columns="fy_reported", values="results_date", aggfunc="count").fillna(0).astype(int)
print("results dates per firm x FY reported (expect 4):")
print(cnt.to_string())
print("\nsource of results date:", ed["source"].value_counts().to_dict())
print("fallback rows (board-meeting outcome only):")
print(ed[ed.source == "board_outcome_fallback"][["firm_id", "results_date", "first_subject"]].to_string(index=False))
