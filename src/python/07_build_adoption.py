"""Adoption dates per panel bank (spec §4) and ai_events_cum.

main : FY of the earliest verified event with deployed = Y and ai_specific = Y
alt1 : FY of the earliest verified AI event of any type
alt2 : first FY where ai_kw exceeds a cutoff and stays above in every later available FY;
       cutoffs = pooled median and pooled 75th percentile of ai_kw over panel bank-FYs
ai_events_cum : cumulative count of verified AI events up to FY end (bank x FY)
Banks with no qualifying event are never-treated (adoption FY = NA). Output: data/interim/adoption.csv,
data/interim/ai_events_cum.csv. Summary <= 20 lines.
"""
import numpy as np
import pandas as pd

from config import FINAL, FIRMS, INTERIM

PANEL = [f[0] for f in FIRMS if f[4]]
ev = pd.read_csv(FINAL / "events_clean.csv", dtype=str)
ev = ev[(ev["verified"] == "Y") & ev["firm_id"].isin(PANEL) & (ev["ai_specific"] == "Y")].copy()
ev["fy"] = ev["fy"].astype(int)

main = ev[ev["deployed"] == "Y"].groupby("firm_id")["fy"].min().rename("adopt_fy_main")
alt1 = ev.groupby("firm_id")["fy"].min().rename("adopt_fy_alt1")
first_ev = ev.sort_values("event_date").groupby("firm_id").first()[["event_id", "event_date"]]

kw = pd.read_csv(INTERIM / "ai_kw.csv", usecols=["bank_id", "fy", "ai_kw"])
kw = kw[kw["bank_id"].isin(PANEL) & kw["ai_kw"].notna()]
cut = {"alt2_p50": kw["ai_kw"].median(), "alt2_p75": kw["ai_kw"].quantile(0.75)}


def first_stay_above(d, c):
    d = d.sort_values("fy")
    above = (d["ai_kw"] > c).to_numpy()
    for i in range(len(above)):
        if above[i:].all():
            return int(d["fy"].iloc[i])
    return np.nan


alt2 = pd.DataFrame({k: kw.groupby("bank_id").apply(first_stay_above, c, include_groups=False) for k, c in cut.items()})
alt2.columns = ["adopt_fy_alt2_p50", "adopt_fy_alt2_p75"]

ad = pd.DataFrame(index=pd.Index(PANEL, name="bank_id"))
ad = ad.join(main).join(alt1).join(alt2).join(first_ev.rename(columns={"event_id": "first_event_id",
                                                                       "event_date": "first_event_date"}))
ad = ad.reset_index()
ad.insert(1, "bank_type", ad["bank_id"].map({f[0]: f[2] for f in FIRMS}))
ad.to_csv(INTERIM / "adoption.csv", index=False)

cum = pd.MultiIndex.from_product([PANEL, range(2011, 2027)], names=["bank_id", "fy"]).to_frame(index=False)
n = ev.groupby(["firm_id", "fy"]).size().rename("n").reset_index().rename(columns={"firm_id": "bank_id"})
cum = cum.merge(n, on=["bank_id", "fy"], how="left").fillna({"n": 0})
before = ev[ev["fy"] < 2011].groupby("firm_id").size()
cum["ai_events_cum"] = cum.groupby("bank_id")["n"].cumsum() + cum["bank_id"].map(before).fillna(0)
cum = cum.drop(columns="n").astype({"ai_events_cum": int})
assert not cum.duplicated(["bank_id", "fy"]).any()
cum.to_csv(INTERIM / "ai_events_cum.csv", index=False)

print(f"verified AI events for panel banks: {len(ev)}; cutoffs ai_kw p50={cut['alt2_p50']:.3f}, p75={cut['alt2_p75']:.3f}")
print(ad.drop(columns=["first_event_date"]).to_string(index=False))
print("never-treated (main):", ad["adopt_fy_main"].isna().sum(), "of", len(ad))
