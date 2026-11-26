"""Append every estimated specification from results/tables to results/spec_log.md (generated section).

Rows between the markers are regenerated on each run; manually written rows above them are kept.
"""
from datetime import date

import pandas as pd

from config import RAW

ROOT = RAW.parent.parent
T = ROOT / "results" / "tables"
LOG = ROOT / "results" / "spec_log.md"
BEGIN, END = "<!-- generated:begin -->", "<!-- generated:end -->"
D = date.today().isoformat()
rows = []


def fmt(x, k=3):
    return "" if pd.isna(x) else f"{x:.{k}f}"


fe = pd.read_csv(T / "fe_results.csv")
for r in fe.itertuples():
    rows.append(f"| {D} | src/R/20_fe.R | {r.outcome} | ai_kw (per 1 SD), term `{r.term}` | 25 banks, n={r.n} | "
                f"{r.spec}; controls(t−1); bank + FY FE; SE clustered by bank | {fmt(r.estimate)} | SE {fmt(r.se)}, "
                f"p={fmt(r.p_cluster)}, wild p={fmt(r.p_wild)} | |")
dd = pd.read_csv(T / "did_results.csv")
if "sample" not in dd.columns:
    dd["sample"] = "all banks"
for r in dd[dd["term"].isin(["overall ATT", "ATT"])].itertuples():
    rows.append(f"| {D} | src/R/21_did.R | {r.outcome} | post_adopt ({r.adoption}) | {r.n_units} banks, {r.sample} | {r.estimator}; "
                f"not-yet-treated; x = baseline age, baseline ln assets | {fmt(r.estimate)} | SE {fmt(r.se)}, p={fmt(r.p)} | "
                f"event-time rows in did_results.csv |")
rb = pd.read_csv(T / "robustness.csv")
for r in rb.itertuples():
    rows.append(f"| {D} | src/R/40_robustness.R | {r.outcome} | `{r.proxy}` (per 1 SD, t−1) | n={r.n} | {r.spec}; "
                f"controls(t−1); bank + FY FE; cluster bank | {fmt(r.estimate)} | SE {fmt(r.se)}, p={fmt(r.p)} | |")
pc = pd.read_csv(T / "fe_psu_check.csv") if (T / "fe_psu_check.csv").exists() else pd.DataFrame()
for r in pc.itertuples():  # POST-HOC (docs/spec_changes.md 2026-11-26)
    rows.append(f"| {D} | src/R/22_psu_check.R (POST-HOC) | {r.outcome} | `ai_l1:psu` (per 1 SD, t−1) | n={r.n} | "
                f"{r.spec}; controls(t−1); cluster bank | {fmt(r.interaction)} | SE {fmt(r.se_int)}, p={fmt(r.p_int)}, "
                f"wild p={fmt(r.p_int_wild)} | PSU slope {fmt(r.psu_slope)} (p={fmt(r.p_psu)}) |")
dp = pd.read_csv(T / "did_posthoc.csv") if (T / "did_posthoc.csv").exists() else pd.DataFrame()
for r in (dp[dp["term"] == "overall ATT"].itertuples() if len(dp) else []):  # POST-HOC (docs/spec_changes.md 2026-11-26)
    rows.append(f"| {D} | src/R/23_did_posthoc.R (POST-HOC) | {r.outcome} | post_adopt (gname_main) | {r.n_treated} treated, "
                f"{r.n_control_never} never/late | {r.spec}; x = {r.xformla} | {fmt(r.estimate)} | SE {fmt(r.se)}, p={fmt(r.p)} | "
                f"joint pre p={fmt(r.pretrend_wald_p)}; leads in did_posthoc.csv |")
ev = pd.read_csv(T / "event_study_tests.csv")
for r in ev.itertuples():
    rows.append(f"| {D} | src/R/30_event_study.R | CAR{r.window} (%) | AI announcement | {r.group}, N={r.N} | "
                f"market model [−250,−30], benchmark {r.benchmark} | mean {fmt(r.mean_car_pct, 2)}% | "
                f"KP-BMP p={fmt(r.p_kp)}, Corrado p={fmt(r.p_corrado)} | r̄={fmt(r.rbar)}; POST-HOC same-firm overlap rule applied (E039 dropped) |")

text = LOG.read_text(encoding="utf-8")
if BEGIN in text:
    text = text[: text.index(BEGIN)].rstrip("\n") + "\n"
block = "\n".join([BEGIN] + rows + [END]) + "\n"
LOG.write_text(text + block, encoding="utf-8")
print(f"spec_log: {len(rows)} generated rows (FE {len(fe)}, DiD {len(dd[dd.term.isin(['overall ATT', 'ATT'])])}, "
      f"robustness {len(rb)}, PSU check {len(pc)}, DiD post-hoc {len(dp[dp.term == 'overall ATT']) if len(dp) else 0}, event study {len(ev)})")
