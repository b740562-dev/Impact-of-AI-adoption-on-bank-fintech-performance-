"""Merge hand-verified event fields onto the candidate list and map events to trading days."""
import numpy as np
import pandas as pd

from config import EVENT_CATEGORIES, EVENT_COMPANIES, FINAL, FIRMS, INTERIM, RAW, fiscal_year

EST_WIN = (-250, -30)
MIN_EST_DAYS = 120
CUTOFF = "15:30"

cand = pd.read_csv(RAW / "events.csv", dtype=str)
ver = pd.read_csv(RAW / "events_verification.csv", dtype=str)
assert cand["event_id"].is_unique and ver["event_id"].is_unique
unknown = set(ver["event_id"]) - set(cand["event_id"])
assert not unknown, f"verification rows without a candidate in events.csv: {sorted(unknown)}"

ev = cand.merge(ver, on="event_id", how="left", suffixes=("_cand", ""), validate="one_to_one", indicator=True)
print("merge:", ev["_merge"].value_counts().to_dict())
for col in ["company", "bank_type", "event_date", "announce_time_ist", "event_title", "category", "ai_technology",
            "ai_specific", "deployed", "source_primary", "source_news"]:
    if f"{col}_cand" in ev:
        ev[col] = ev[col].combine_first(ev[f"{col}_cand"]) if col in ev else ev[f"{col}_cand"]
ev["verified"] = ev["verified"].fillna("N")
ev = ev.drop(columns=[c for c in ev.columns if c.endswith("_cand")] + ["_merge"])

ev["firm_id"] = ev["company"].map(EVENT_COMPANIES)
assert ev["firm_id"].notna().all(), ev.loc[ev["firm_id"].isna(), "company"].unique()
ev["category"] = ev["category"].str.strip().str.lower()
bad_cat = ev.loc[(ev["verified"] == "Y") & ~ev["category"].isin(EVENT_CATEGORIES), ["event_id", "category"]]
assert bad_cat.empty, bad_cat

v = ev["verified"] == "Y"
date = pd.to_datetime(ev["event_date"], format="%Y-%m-%d", errors="coerce")
assert date[v].notna().all(), ev.loc[v & date.isna(), ["event_id", "event_date"]]
for col in ["source_primary", "source_news"]:
    missing = ev.loc[v & ev[col].isna(), "event_id"].tolist()
    assert not missing, f"verified events without {col}: {missing}"
ev["event_date"] = date.dt.strftime("%Y-%m-%d")
ev["fy"] = fiscal_year(date.dt).astype("Int64")

# ---- trading-day mapping (NSE calendar = Nifty 500 trading days) ----
px = pd.read_parquet(INTERIM / "prices_daily.parquet", columns=["id", "date", "adj_close"])
cal = pd.DatetimeIndex(sorted(px.loc[px["id"] == "NIFTY500", "date"].unique()))
after_close = ev["announce_time_ist"].fillna("").str.match(r"^\d{2}:\d{2}$") & (ev["announce_time_ist"].fillna("") > CUTOFF)
effective = date + pd.to_timedelta(after_close.astype(int), unit="D")
pos = cal.searchsorted(effective.fillna(pd.Timestamp("2100-01-01")))
in_cal = date.notna() & (pos < len(cal))
ev["event_trade_date"] = pd.Series(pd.NaT, index=ev.index)
ev.loc[in_cal, "event_trade_date"] = cal[pos[in_cal]]
ev["after_close"] = np.where(after_close, "Y", "N")

# ---- estimation-window eligibility (firm's own valid trading days in [-250, -30]) ----
firm_days = {k: pd.DatetimeIndex(g["date"].sort_values()) for k, g in px.groupby("id")}
n_est, listed = [], []
for _, r in ev.iterrows():
    td = r["event_trade_date"]
    if pd.isna(td):
        n_est.append(np.nan); listed.append(np.nan); continue
    k = cal.get_loc(td)
    lo, hi = cal[max(k + EST_WIN[0], 0)], cal[k + EST_WIN[1]]
    days = firm_days[r["firm_id"]]
    n_est.append(int(((days >= lo) & (days <= hi)).sum()))
    listed.append("Y" if days.min() <= td else "N")
ev["listed_at_event"] = listed
ev["n_est_days"] = pd.array(n_est, dtype="Int64")
event_study_firms = {f[0] for f in FIRMS if f[5]}  # CARs only for the 14 event-study firms (CLAUDE.md §3a)
ev["car_eligible"] = np.where(v & ev["firm_id"].isin(event_study_firms) & (ev["listed_at_event"] == "Y")
                              & (ev["n_est_days"] >= MIN_EST_DAYS) & (ev["ai_specific"] == "Y"), "Y", "N")
ev["event_trade_date"] = pd.to_datetime(ev["event_trade_date"]).dt.strftime("%Y-%m-%d")

# ---- earnings screen: results announcement within +/-3 trading days (results after 15:30 -> next day) ----
ed_path = INTERIM / "earnings_dates.csv"
ev["earnings_within_3d"] = pd.NA
if ed_path.exists():
    ed = pd.read_csv(ed_path)
    rd = pd.to_datetime(ed["results_date"]) + pd.to_timedelta((ed["after_close"] == "Y").astype(int), unit="D")
    ed["k"] = cal.searchsorted(rd)
    covered = set(ed["firm_id"])
    for i, r in ev.iterrows():
        if pd.isna(r["event_trade_date"]) or r["firm_id"] not in covered:
            continue
        k = cal.get_loc(pd.Timestamp(r["event_trade_date"]))
        near = ed.loc[ed["firm_id"] == r["firm_id"], "k"].sub(k).abs().le(3).any()
        ev.loc[i, "earnings_within_3d"] = "Y" if near else "N"

# Same firm, overlapping [-5,+5] windows: flag for the event-study script to handle.
ev = ev.sort_values(["firm_id", "event_trade_date"])
ev["overlap_prev_11d"] = "N"
for fid, g in ev[ev["car_eligible"] == "Y"].groupby("firm_id"):
    idx = [cal.get_loc(pd.Timestamp(d)) for d in g["event_trade_date"]]
    for (i, k), kp in zip(list(zip(g.index, idx))[1:], idx[:-1]):
        if k - kp <= 10:
            ev.loc[i, "overlap_prev_11d"] = "Y"

order = ["event_id", "firm_id", "company", "bank_type", "sample", "event_date", "announce_time_ist", "after_close",
         "event_trade_date", "fy", "event_title", "category", "ai_technology", "ai_specific", "deployed",
         "verified", "listed_at_event", "n_est_days", "car_eligible", "overlap_prev_11d", "earnings_within_3d",
         "source_primary", "primary_type", "source_news", "news_date", "verify_note", "checked_on", "key_note"]
ev = ev[[c for c in order if c in ev.columns]].sort_values(["firm_id", "event_date", "event_id"])
FINAL.mkdir(parents=True, exist_ok=True)
ev.to_csv(FINAL / "events_clean.csv", index=False)

# ---- diagnostics ----
print(f"\nevents: {len(ev)}  verified: {v.sum()}  CAR-eligible: {(ev.car_eligible == 'Y').sum()}")
print("\nverified by firm:")
print(ev[ev.verified == "Y"].groupby(["bank_type", "firm_id"]).size().to_string())
print("\nfirms with verified events:", ev.loc[ev.verified == "Y", "firm_id"].nunique())
print("\nnot verified:", ev.loc[ev.verified != "Y", "event_id"].tolist())
print("\nverified but not CAR-eligible:")
print(ev.loc[(ev.verified == "Y") & (ev.car_eligible == "N"),
             ["event_id", "firm_id", "event_date", "listed_at_event", "n_est_days", "ai_specific"]].to_string(index=False))
print("\nsame-firm overlaps within 10 trading days:", ev.loc[ev.overlap_prev_11d == "Y", "event_id"].tolist())
