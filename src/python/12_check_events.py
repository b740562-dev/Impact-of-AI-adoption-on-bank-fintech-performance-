"""Consistency checks on data/final/events_clean.csv. Summary <= 20 lines; every flagged row in logs/events_check.log."""
import re

import pandas as pd

from config import EVENT_CATEGORIES, FINAL, FIRMS, RAW

ROOT = RAW.parent.parent
LOG = ROOT / "logs" / "events_check.log"
LOG.parent.mkdir(exist_ok=True)
ev = pd.read_csv(FINAL / "events_clean.csv", dtype=str)
v = ev[ev["verified"] == "Y"].copy()
types = {f[0]: f[2] for f in FIRMS}
es_firms = {f[0] for f in FIRMS if f[5]}
listing = pd.read_csv(RAW / "prices" / "_manifest.csv").set_index("id")["first_date"]
cw = pd.read_csv(RAW / "crisis_windows.csv")
d = pd.to_datetime(v["event_date"], errors="coerce")
nd = pd.to_datetime(v["news_date"], errors="coerce")
checks = {
    "missing event_date": d.isna(),
    "missing source_primary": v["source_primary"].isna(),
    "missing source_news": v["source_news"].isna(),
    "missing news_date": nd.isna(),
    "news dated BEFORE event date (event date may be late)": nd < d,
    "news > 30 days after event date": (nd - d).dt.days > 30,
    "category not allowed": ~v["category"].str.lower().isin(EVENT_CATEGORIES),
    "ai_specific not Y": v["ai_specific"] != "Y",
    "deployed not Y/N": ~v["deployed"].isin(["Y", "N"]),
    "bank_type mismatch": v["bank_type"] != v["firm_id"].map(types),
    "sample label vs firm list": (v["sample"] == "event_study") != v["firm_id"].isin(es_firms),
    "verified but note says REJECT": v["verify_note"].fillna("").str.contains("REJECT"),
    "CAR-eligible but pre-listing": (v["car_eligible"] == "Y") & (pd.to_datetime(v["event_trade_date"]) < pd.to_datetime(v["firm_id"].map(listing))),
    "event-study firm, earnings flag missing": v["firm_id"].isin(es_firms) & v["earnings_within_3d"].isna() & (v["listed_at_event"] == "Y"),
    "primary_type vs URL": ((v["primary_type"] == "exchange_filing") & ~v["source_primary"].fillna("").str.contains(r"bseindia|nseindia|nsearchives|/ir/|analyst|investor", case=False))
                           | ((v["primary_type"] == "annual_report") & v["source_primary"].fillna("").str.contains(r"bseindia\.com.*AttachHis", case=False) & False),
    "source URL malformed": ~v["source_news"].fillna("http").str.match(r"https?://") | ~v["source_primary"].fillna("http").str.match(r"https?://|.*annual report", case=False),
    "trade date before event date": pd.to_datetime(v["event_trade_date"]) < d,
}
cw_hit = [any((r.firm_id == c.firm_id) and (c.start <= r.event_trade_date <= c.end) for c in cw.itertuples()) for r in v.itertuples()]
checks["in a crisis window (excluded from CARs)"] = pd.Series(cw_hit, index=v.index)
dup_date = v.duplicated(["firm_id", "event_date"], keep=False)
dup_title = v.assign(t=v["event_title"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True)).duplicated(["firm_id", "t"], keep=False)
checks["duplicate firm + date"] = dup_date
checks["duplicate firm + title"] = dup_title
checks["same-firm overlap within 10 trading days"] = v["overlap_prev_11d"] == "Y"

with open(LOG, "w", encoding="utf-8") as f:
    for name, m in checks.items():
        m = m.fillna(False).astype(bool)
        if m.any():
            print(f"\n## {name} ({m.sum()})", file=f)
            print(v.loc[m, ["event_id", "firm_id", "event_date", "news_date", "event_trade_date", "event_title"]]
                  .to_string(index=False), file=f)
print(f"events: {len(ev)}, verified: {len(v)}")
for name, m in checks.items():
    n = int(m.fillna(False).astype(bool).sum())
    if n:
        print(f"  {n:3d}  {name}")
print(f"details: {LOG}")
