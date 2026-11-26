# Results summary

Status as of 2026-11-26 (tags `day2-panel`, `day3-results`). All estimated specifications are listed in
`results/spec_log.md`; spec changes are in `docs/spec_changes.md`. Numbers only; no interpretation beyond them.

**Pending updates:** (1) Phase 2b and the robustness table use the round-3 events (54 verified). `ai_events_cum`
results are unchanged by them: all new events fall in FY2026 or later and enter only with a one-year lag (beyond the
panel). Phase 3 is unaffected (the new events are panel-only banks). (2) `ai_calls` (transcripts) is not yet in the panel. (3) `ai_patents` is dropped: the pre-specified Google Patents
search finds 0 AI patent applications for all 25 banks (1 filing in total), so the proxy has no variation
(`docs/spec_changes.md`).

## Data
- Verified AI events: 54 of 88 candidates, across 25 firms; 39 CAR-eligible; 31 used in the event study after
  excluding earnings (±3 trading days) and crisis windows.
- Firm panel: 392 bank-FYs, 25 banks, FY2011–FY2026 (accounting variables to FY2025). Main adoption definition:
  19 of 25 banks treated within the window (5 of them in FY2026, when only stock returns are observed);
  6 never-treated (Central, UCO, BoM, KVB, DCB; Indian Bank adopts in FY2027).
- `ai_kw`: 387 of 400 annual reports; SD = 1.47 AI terms per 10,000 English words.

## Phase 1: sector level (descriptive)
Assets-weighted `ai_kw` rose from about 0.02 (FY2011–16 mean) to 1.26 (FY2017–25) for the sector (Welch p = 0.004),
1.67 for private banks (p < 0.001) and 1.04 for PSU banks (p = 0.008). Over the same split, mean ROE changed by
−5.4 pp for the sector (p = 0.12), −4.4 pp for private banks (p = 0.012) and −7.0 pp for PSU banks (p = 0.17). In OLS of
ROE_t on `ai_kw`_(t−1) and GDP growth (FY2012–25, n = 14 per level), the `ai_kw` coefficient is +2.17 pp (SE 3.07,
p = 0.50) for the sector, −1.49 pp (SE 1.36, p = 0.30) for private and +5.00 pp (SE 4.60, p = 0.30) for PSU banks.
Adding demonetisation, AQR and COVID dummies gives −0.84 (p = 0.79), −2.73 (p = 0.11) and +0.93 (p = 0.84).

## Phase 2a: two-way fixed effects (main proxy `ai_kw`)
Bank and FY fixed effects, controls lagged one year (ln assets, CRAR, loan-to-deposit, liquidity, GNPA, PCA); SEs
clustered by bank (25 clusters); wild cluster bootstrap p (Webb, 9,999 draws). Effects per 1 SD of `ai_kw`, lag 1
(pre-specified main):
- ROE: +0.13 pp (SE 0.73, p = 0.86, wild p = 0.86, n = 336).
- Stock return: −1.72 % (SE 4.38, p = 0.70, wild p = 0.76, n = 353).
- ROA: +0.01 pp (SE 0.05, p = 0.76, wild p = 0.76). Tobin's Q: −0.006 (SE 0.005, p = 0.29, wild p = 0.33).
- Lag 0: ROE +0.94 pp (p = 0.34); stock return +8.19 % (SE 2.74, p = 0.006, wild p = 0.039). Lag 2: ROE −2.85 pp
  (p = 0.10, wild p = 0.051); stock return −4.28 % (p = 0.34).
- AI × PSU (lag 1): ROE +4.39 pp (SE 1.49, p = 0.007, wild p = 0.007), with the private-bank slope −3.20 pp
  (p = 0.038, wild p = 0.037); stock return +2.20 % (p = 0.78); ROA +0.22 pp (p = 0.09, wild p = 0.10);
  Tobin's Q +0.02 (p = 0.24).
- Other interactions are in `results/tables/fe_results.csv`. AI × baseline age on ROE is +1.99 pp (p = 0.033).
  AI × demonetisation on stock return is −161 % (p = 0.012) and is identified from a single FY.

## Phase 2b: staggered DiD (`post_adopt`, effect of post_adopt = 1)
Callaway–Sant'Anna (not-yet-treated controls, x = baseline age and baseline ln assets) and Sun–Abraham:
- Main adoption (first deployed AI): ROE −23.9 pp (SE 8.4, p = 0.004; Sun–Abraham −6.9 pp, p = 0.004); stock return
  −37.2 % (SE 11.2, p = 0.001; Sun–Abraham −19.1 %, p = 0.010).
- Alt 1 (first AI event): ROE −25.2 pp (p = 0.003; Sun–Abraham −7.0, p = 0.005); stock return −40.0 % (p < 0.001;
  Sun–Abraham −21.4 %, p = 0.006).
- Alt 2 (`ai_kw` thresholds, CS): ROE −2.0 pp (p50, p = 0.47) and +1.1 pp (p75, p = 0.28); stock return −24.9 % (p = 0.37)
  and +12.9 % (p = 0.45).
- ROE estimates are unchanged by the round-3 events: the new adoptions are in FY2026, after the last accounting year,
  so those banks act as controls through FY2025 either way.
- Pre-period event-time estimates (main, CS): ROE −2.6 to +4.1 pp, three individually significant (e = −7, −6, −4).
  Stock return e = −9 to −1: −12.9 to +28.6 %, none significant (p ≥ 0.23); the longer leads now reach e = −14, and
  e = −11 (−51.7 %, p = 0.001) and e = −10 (+39.8 %, p = 0.005) are individually significant, with opposite signs.
- Post-hoc, excluding Yes Bank: ROE −21.1 pp (p = 0.036); stock return −34.8 % (p = 0.012).

## Phase 3: event study (CARs)
Market model, estimation window [−250, −30], Nifty 500 benchmark, N = 31 events:
- All events: CAR[−1,+1] +0.13 % (Kolari–Pynnönen p = 0.81, Corrado p = 0.49); CAR[−5,+5] −1.28 % (p = 0.46, 0.20).
- PSU (N = 8): CAR[−5,+5] −2.70 % (KP p = 0.041, Corrado p = 0.047); with Nifty Bank −2.83 % (p = 0.21, 0.09).
- Private (N = 14), NBFC (N = 4) and fintech (N = 5): no CAR significant at 5 % under either test.
- Caveat: two Paytm events one trading day apart (E070 2025-10-06, E039 2025-10-07) are both included, so their
  event windows overlap and the same returns are counted twice (CAR[−1,+1] +4.4 % and +3.1 %).

## Robustness (FE, per 1 SD of proxy at t−1)
`ai_kw` on ROE: baseline +0.10 pp (p = 0.86), winsorised +0.11 (p = 0.85), + lagged profit growth +0.27 (p = 0.67),
year-standardised −0.51 (p = 0.43), ln(1+count) −0.80 (p = 0.40), excluding merger years +0.04 (p = 0.95). On stock
return all `ai_kw` variants have p ≥ 0.68. Other proxies: `ai_events_cum` ROE −1.85 pp (p = 0.008), stock return −7.06 %
(p = 0.017); `fintech_idx` ROE +1.59 pp (p = 0.37), stock return +12.71 % (p = 0.040).
