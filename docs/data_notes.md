# Data notes

## Downloads log
Every raw download: file, source URL, date downloaded, notes. Large raw files are gitignored; this log is how to re-create them.

| File / folder | Source URL | Downloaded | Notes |
|---|---|---|---|
| data/raw/prices/*.csv (30 firms + 2 indices) | Yahoo Finance via `yfinance` (`src/python/01_download_prices.py`), tickers in `src/python/config.py` | 2026-11-25 | Daily OHLC, close, adjusted close (splits + dividends), volume, 2009-01-02 onward. Gitignored; re-run the script to rebuild. Indices: Nifty 500 = `^CRSLDX`, Nifty Bank = `^NSEBANK` (Yahoo, used in place of niftyindices.com for now; cross-check pending). |
| data/raw/rbi/T01_liabilities_assets.xlsx, T02_earnings_expenses.xlsx, T03_crar.xlsx, T06_npa_movement.xlsx, T11_select_ratios.xlsx | RBI DBIE (https://data.rbi.org.in) → Publications → Time-Series Publications → Statistical Tables Relating to Banks in India → Tables based on Annual Accounts → Table 1, 2, 3, 6, 11 → Export → Excel (all reports, all filters = All Values) | 2026-11-25 | Coverage FY2005–FY2025 (as on 31 March). Gitignored; re-export manually from DBIE (no stable download URL). |
| Table 10 (Bank Group-wise Select Ratios) | same path, Table 10 | not obtained | DBIE export failed server-side in Excel and TXT (2026-11-25, error "[object ArrayBuffer]"). Phase 1 group ratios are computed instead from the group subtotal rows in Tables 1, 2, 6 (same publication, same formulas as bank level). |

## RBI financials: parsing and definitions (2026-11-25)
Script: `src/python/02_clean_rbi.py` → `data/interim/rbi_long.parquet` (all banks, all items), `rbi_bank_financials.csv` (25 panel banks × FY2005–25), `rbi_group_financials.csv` (PSU, Private, Nationalised, SBI group, Foreign, SFB, Payments, All SCB).
- Amounts in ₹ crore. RBI symbol "-" (nil) → 0 in amount tables, NA in ratio tables; ".." → NA.
- Trailing "*" / "#" on bank names are RBI footnote markers (merged entities in Table 6: SBI FY2018, BoB FY2020, PNB/Canara/Union/Indian FY2021) and are stripped before matching.
- IDFC Bank Ltd (FY2016–18) and IDFC First Bank Ltd (FY2019+) both map to `IDFCFIRST`; the panel keeps FY2019+ only (CLAUDE.md §3b).
- ROE = PAT / average(capital + reserves, t and t−1) × 100. ROA = PAT / average total assets × 100. Matches RBI Table 11 ROE exactly (corr 1.000) and ROA closely (corr 0.993, median |diff| 0.02 pp; RBI ROA denominator differs slightly).
- Gross NPA ratio = gross NPA / gross advances × 100, with gross advances = net advances (balance sheet) + gross NPA − net NPA. Approximation: adds back NPA provisions only.
- Liquidity ratio = (cash + balances with RBI + balances with banks in India and abroad + money at call) / total assets × 100. Government securities excluded.
- CRAR: Basel III total where available, else Basel II, else Basel I; identical to Table 11 CRAR.
- Loan-to-deposit = advances / deposits × 100. Cost-to-income = operating expenses / (NII + other income) × 100.
- Checks: balance-sheet identity holds for all bank-years (|assets − liabilities| ≤ ₹1 crore). No missing outcome/control cells for FY2011–25 except IDFC FY2016 (first year, outside panel window).
- **RBI Table 11 error:** Bank of India FY2016 ROA shown as +0.94; BOI reported a net loss that year (our PAT-based ROA −0.99). We use the computed ROA; `roa_rbi` kept only for cross-checking.
- Spot checks vs reported results: HDFC FY2025 PAT ₹67,347 cr; SBI FY2025 PAT ₹70,901 cr, GNPA 1.82%; PNB FY2018 GNPA 18.36%.
- **FY2026 not yet in RBI tables** (2025-26 edition expected around Dec 2026). FY2026 financials must come from annual reports; each fill to be logged under "Gap fills".

## Panel, adoption, founding years, crisis windows (2026-11-26)
- `data/final/panel.parquet` (`src/python/04_build_panel.py`): 392 bank-FYs, 25 banks, FY2011–26 (IDFC First FY2019+). Controls lagged one year; `gname_*` = adoption FY (0 = never treated). Merge diagnostics and missing-value table: `logs/panel.log`.
- Adoption (`07_build_adoption.py`, `data/interim/adoption.csv`): main = first verified deployed AI event; 15 of 25 banks treated, 10 never-treated (BOI, Indian, Central, IOB, UCO, BoM, PSB, KVB, SIB, DCB), because they have no verified AI event yet. alt2 cutoffs: pooled `ai_kw` median 0.072 and p75 1.196.
- Founding years: `data/raw/founding_years.csv` (hand-curated with sources; rule = year the bank began under its current legal identity, e.g. SBI 1955, Kotak 2003 banking licence). 14 come from annual-report quotes and 11 from web sources. The Wikipedia API returned HTTP 429 and was not retried.
- Event-study crisis windows: `data/raw/crisis_windows.csv` with sources. Paytm's end date (2024-03-15, RBI's extended deadline) and IndusInd's window (2025-03-10 to month end) are interpretations of the spec's "from 2024-01-31" and "Mar 2025".
- `fintech_idx` (`src/python/08_fintech_index.py` → `data/interim/fintech_idx.csv`): RBI monthly releases https://rbi.org.in/scripts/NEFTUserView.aspx?Id=1..232 (cached in `data/raw/mobile_banking/`, gitignored; downloaded 2026-11-26). Title variants ("Bank-wise", "Bank wise", "Bankwise") are all parsed; bank names are mapped by pattern, and the matched RBI names are listed in `logs/fintech.log`. Coverage: volume FY2013–FY2026 (RBI bank-wise mobile data start in 2012), all 25 banks from FY2018; FY2011–12 NA. Feature dummies come from annual-report first mentions (median first FY: mobile app 2014, UPI 2017, chatbot 2019, video-KYC 2021, voice assistant 2022). The volume is min–max scaled over all bank-FYs, so it is dominated by SBI's scale.
- Not built yet: `ai_patents` (needs BigQuery credentials). `ai_calls`: script `src/python/09_transcripts.py` written, to be run by the user.

## RBI Prompt Corrective Action (`pca`) (2026-11-26)
Script `src/python/06_build_pca.py` (requests only) → `data/interim/pca_spells.csv`, `data/interim/pca_bank_fy.csv` (`pca_months` = FY months with ≥15 days under PCA; `pca` = 1 if ≥ 6). Details in `logs/pca.log`; raw BSE hits in `data/raw/pca/` (gitignored).

| Bank | Entry | Entry basis / source | Exit | Exit source (RBI press release) |
|---|---|---|---|---|
| Bank of India | 2017-12-19 | RBI letter date quoted in BSE filing of 2017-12-20: https://www.bseindia.com/xml-data/corpfiling/AttachHis/ce89c4a8-8151-46f1-a078-d499288a7806.pdf | 2019-01-31 | https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=46165 |
| Bank of Maharashtra | 2018-03-16 (`entry_inferred` = 1) | No BSE filing found (2015–18 search); entry "on or before" PIB release: https://www.pib.gov.in/newsite/PrintRelease.aspx?relid=177591 | 2019-01-31 | https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=46165 |
| UCO Bank | 2017-05-05 | RBI letter date quoted in BSE filing of 2017-05-12: https://www.bseindia.com/xml-data/corpfiling/AttachHis/883d37e8-88da-451b-b8c9-eb915150f675.pdf | 2021-09-08 | https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=52198 |
| Indian Overseas Bank | 2015-10-05 | IOB BSE announcement 2015-10-05 19:22 ("RBI has initiated a Prompt Corrective Action on the Bank"); letter date not stated, filing date used; no attachment | 2021-09-29 | https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=52318 |
| Central Bank of India | 2017-06-13 | RBI letter date quoted in BSE filing of 2017-06-14: https://www.bseindia.com/xml-data/corpfiling/AttachHis/82cd3df6-cc69-4858-92d0-b873fe9118df.pdf | 2022-09-20 | https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=54395 |

- Cross-check: all five banks appear in the PIB release of 2018-03-16 (eleven PSBs under PCA).
- Caveats: BOM's true entry is likely earlier than the PIB date (no filing found on BSE; NSE not searched). IOB's 2015 entry predates RBI's revised PCA framework (April 2017); the spell is treated as continuous until the 2021 exit.

## GDP growth (Phase 1) (2026-11-25)
- `data/raw/gdp/real_gdp_growth_dbie.csv`: RBI DBIE report "Components of Gross Domestic Product (Growth Rate)", GDP at market prices, 2011-12 base (back series), constant and current prices, FY2010–FY2026. DBIE Excel export failed server-side ("[object ArrayBuffer]"), so the values were extracted from the rendered report text in the browser (2026-11-25). Phase 1 uses constant-price growth (percent). A 2022-23-base series exists only from FY2024 and is not used.

## Events: research round 2 (2026-11-25)
- New events from round 2 are in `data/raw/events_additions.csv` (E061–E078; hand-curated research output with sources and verdicts). `data/raw/events.csv` (user's candidate list) is not edited. Verdict updates for existing events are in `data/raw/events_verification.csv`.
- Status: 78 candidates, 48 verified across 20 firms, 39 CAR-eligible.
- Overlapping same-firm events (2026-11-26, `src/python/12_check_events.py`): Paytm E070 (Playback, 2025-10-06) and E039 (AI Soundbox, 2025-10-07) are one trading day apart and both enter the event study; their [−5,+5] windows overlap, so the same Paytm returns are counted twice. Both kept by decision (no rule in the spec); reported as a caveat. Paytm E069/E071/E072 also overlap but are excluded by the earnings screen.
- Unverified first-AI leads for adoption dates (annual-report only, no dated news): Union UVA FAQ chatbot FY2018; PNB PIHU FY2020; BoB Baroda Brainy FY2018; Bank of India BOI Seva 2019-09-07; UCO UMA FY2021; IOB Buddy FY2026; Federal Niki.ai FedMobile bot 2018-01-19 (news only); RBL ChatPay FY2018; Yes mPower 2017-01-05 (news only); Canara CANDI humanoid 2017-07-27 (AR does not say AI); Indian Bank ADYA 2021-04-01 (dated news blocked).

## Events: research round 3, never-treated banks (2026-11-26)
- Scope: the 10 banks with no main adoption date (BOI, Indian, Central, IOB, UCO, BoM, PSB, KVB, SIB, DCB). Rule applied strictly
  (user decision 2026-11-26): a bank document as primary source AND a dated news publication; vendor case studies, bank
  social posts, awards and executive interviews do not count as news.
- Verified (E079–E083 new, E048 updated): BOI MuleHunter.AI 2025-08-01 (news reports an RBI official naming BOI; go-live
  earlier, unknown); PSB MuleHunter.AI 2025-11-12 (paid press release; AR says adopted Sep 2025); IOB Buddy chatbot 2026-03-06
  (date from the bank's own post; only news is 2026-07-20); SIB AI/ML document generation 2026-01-15 (market-summary news
  site) and Zeni AI CoE 2026-05-06; Indian Bank AI-TARA 2026-09-10 (FY2027).
- Not verified (recorded with verified = N, E084–E088 new, E053/E058/E060 notes updated): BoM predictive ML model 2023-02-10
  (news does not name the model); UCO UMA chatbot FY2021; Central Cent Chanakya FY2024/25; DCB Ringg voice AI (vendor case
  study only); KVB AI video KYC FY2021; Indian Bank ADYA 2021-04-01 (bank release says AI; news still blocked); SIB SOnA; BOI SEVA.
- Result: main adoption dates for 19 of 25 banks; never-treated within FY2011–26: Central, UCO, BoM, KVB, DCB, and Indian
  Bank (adoption FY2027 is after the panel window, so `gname_*` = 0; `04_build_panel.py`). Five banks adopt in FY2026, when
  only stock returns are observed (accounting variables end FY2025).
- Blocked URLs that could upgrade unverified events (open manually): thenfapost.com/2021/04/02/indian-bank-launches-its-new-vision-and-mission-statement/
  and Business Standard 121040101119 (ADYA); pressreader Banking Frontiers 2019-10-20 (BOI SEVA); southindianbank.bank.in
  Q2 FY26 deck (may date SIB earlier, same FY).

## BSE corporate announcements (2026-11-25)
- Source: BSE public announcements listing `api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w` (per scrip, quarterly windows, 50 rows/page), attachments from `bseindia.com/xml-data/corpfiling/AttachHis|AttachLive/`. Script `src/python/04_scrape_announcements.py`, 0.7 s between requests. Transient HTTP 400/5xx are retried 3 times with backoff; 401/403/429 stop the run (none occurred). Raw files `data/raw/bse_announcements/{firm}.csv`, `_all.csv`, `pdf/` are gitignored; re-run the script to rebuild.
- Coverage: 14 event-study firms, 2015-01-01 to 2026-11-25, 27,691 announcements.
- AI screen: CLAUDE.md dictionary on subject + headline; attachment text (first 6 pages) scanned for press/media-release, launch, partnership, MoU and investment filings. Output `data/interim/events_scraped.csv` (27 matches, 3 already in events.csv: E019, E038, E039). Most attachment-only matches are quarterly results press releases mentioning AI in passing and are not events.
- New candidate leads from the scrape (not yet in events.csv): HDFC investment in Lentra AI CCDs (2019-11-21 14:39); Paytm–Amadeus AI travel partnership (2023-11-15 15:59); Paytm GIFT City AI-driven remittance plan (2024-01-10 08:36); Paytm–Groq real-time AI partnership (2025-11-05 08:01).

## Quarterly results dates (2026-11-25)
- `src/python/05_earnings_dates.py` → `data/interim/earnings_dates.csv` from the same BSE pull: first results filing per firm-quarter (BSE category "Result", else results named in the subject, else a board-meeting outcome in a results month: 8 cases, labelled `board_outcome_fallback`). 593 results dates; 4 per firm-year except HDFC FY2018 and FY2022, IndusInd FY2018 (3 each) and partial listing years.
- `earnings_within_3d` is computed in `02_clean_events.py` (results after 15:30 shifted to the next trading day; ±3 trading days) and written to `data/final/events_clean.csv`; `data/raw/events.csv` is not edited (CLAUDE.md §10). Panel-only banks are not covered (no CAR for them).

## Annual reports and `ai_kw` (2026-11-25)
- Source: BSE annual-report filings (public listing `api.bseindia.com/.../AnnualReport_New/w?scripcode=<code>`, PDFs under `bseindia.com/xml-data/corpfiling/AttachHis/`). Script `src/python/01_download_annual_reports.py`; index of every listing with URL, filing/revision timestamps and the selected file in `data/raw/annual_reports/_index.csv` (gitignored with the PDFs; each PDF has a `.url` sidecar with its source). Re-run the script to rebuild.
- Selection per bank-FY: latest full English filing. Resubmissions that are Hindi editions, errata or corrigenda are not selected (Union FY2024/FY2025 Hindi editions, Canara FY2023 errata, Federal FY2023 corrigendum).
- Coverage: 387 of 400 bank-FY cells (FY2011–26). **Missing:** RBL FY2011 and IDFC First FY2011–14 (not yet listed); PNB FY2025, Kotak FY2024, KVB FY2019 and FY2023–26 (not on BSE listing); KVB FY2016 (BSE file is corrupt: zero bytes). IOB FY2013 BSE file is a 1-page document → `ai_kw` NA. To fill from bank IR sites later; log each fill under "Gap fills".
- `src/python/03_ai_keywords.py` (dictionary in `src/python/ai_terms.py`) → `data/interim/ai_kw.csv` / `ai_keywords.parquet`: raw counts per term, `total_words` (English words, see spec_changes.md), `tokens_raw`, `ai_kw` per 10,000 English words, `ai_kw_z` (z-score within FY). Random matched snippets for false-positive review: `data/interim/ai_kw_snippets.csv`.
- False-positive rules (all logged in spec_changes.md): "Air India"; "LLMS" (Loan Lifecycle Management System); "LLM" as law degree; acronyms (LLM/NLP/RPA) inside legacy-font Hindi gibberish; "AI" = artificial insemination in livestock CSR programmes (IDFC First FY2026). Remaining known noise: awards ("Best AI & ML Bank"), training mentions and macro commentary are counted, as the dictionary rules imply.

## Market capitalisation and Tobin's Q (2026-11-25)
Script: `src/python/02_build_market_cap.py` → `data/interim/market_cap_fy.csv` (25 panel banks × FY-end, FY2009–FY2025).
- Shares (crore) = RBI Table 1 paid-up capital (₹ crore) / face value. Face value today and the face-value sub-divisions are in `config.py` (`FACE_VALUE_NOW`, `FV_SPLITS`). Every sub-division is checked to exist in Yahoo's split records. Yahoo also records bonus issues as "splits"; bonuses change paid-up capital, not face value, so they are not FV events.
- Actual FY-end price = Yahoo close (which is split/bonus adjusted) × product of all later Yahoo split factors. Market cap (₹ crore) = actual FY-end close × shares.
- Tobin's Q = (market cap + total assets − (capital + reserves)) / total assets.
- Checks: (1) market cap is continuous across every face-value split (FY ratio 0.75–1.94, while the actual price falls by the split factor). (2) Latest close × FY2025 capital / current face value vs yfinance current market cap for SBI, ICICI, Axis, PNB, BoB: differences −3.3% to +0.1% (all within 5%).
- **Preference capital:** RBI "Capital" includes perpetual non-cumulative preference shares (mostly held by GoI) for some bank-years, which would overstate the equity share count. Market cap, shares and Tobin's Q are set to NA (39 bank-years, `pref_capital_flag` gives the evidence): Central FY2009–14, Indian FY2009–13, UCO FY2009–13, Punjab & Sind FY2009–21, Bank of Maharashtra FY2009–15, Kotak FY2019–23. Evidence comes from annual-report Schedule 1 text and share-count breaks. These can be filled later from the equity share counts in annual-report Schedule 1. Other bank-years may also contain small preference amounts that are not yet detected.
- FY2026: NA (RBI capital not yet published; see spec_changes.md).

## Prices: checks and flags (2026-11-25)
- Listing-date starts in the Yahoo series: PSB 2010-12-30, IDFC First 2015-11-06 (IDFC Bank listing; panel uses FY2019+ only), RBL 2016-08-31, SBI Cards 2020-03-16, PB Fintech 2021-11-15, Paytm 2021-11-18.
- Corporate actions recorded by Yahoo (adjusted close accounts for them): HDFC 2011, 2019, 2025-08-26 (1:1 bonus); Kotak 2010, 2015, 2026-01-14; SBI 2014; Canara 2024; Bajaj Finance 2016, 2025; and others (see `splits` column in raw files).
- Download-day bar dropped as possibly incomplete. 2026-11-24 missing in all series (market holiday).
- 14 daily moves with |return| > 30% are listed in `data/interim/price_flags_extreme.csv`; `returns_fy.csv` carries `n_extreme_days` per firm-FY.
  - Genuine market moves: PSU recapitalisation rally 2017-10-25 (BOB, BOI, Canara, PNB, Union); IndusInd 2020-03-26; Yes Bank 2019-10-03 and March 2020 reconstruction; PB Fintech 2026-09-24 (−36% on 27M shares, cause still to be checked; falls inside the event-study period).
  - **Suspect data: Karur Vysya 2011-05-04 (+30%).** Pre-May-2011 bars have very low volume and prices that look scaled differently; likely an unadjusted corporate action in Yahoo. Affects KVB FY2012 return. Cross-check against NSE bhavcopy before use.
  - **2026-11-25: KVB FY2012 `stock_ret_pct` set to NA** (`SUSPECT_RET` in `src/python/02_clean_prices.py`; reason in the `ret_note` column of `returns_fy.csv`). Reason: Yahoo series before May 2011 is suspect (unadjusted corporate action), so the FY2012 return (31 Mar 2011 → 30 Mar 2012) straddles the break. KVB FY2011 is kept because its start and end prices both lie in the pre-May-2011 segment; daily KVB prices before 2011-05-04 should not be used.
- Fiscal-year total return (`stock_ret_pct`, percent) = last adjusted close of FY / last adjusted close of prior FY − 1. Set to NA if the firm was not trading by the start of the FY. Coverage FY2010–FY2026.

## Gap fills
Values filled from annual reports where RBI tables lack coverage.

| bank | fy | variable | value | source | note |
|---|---|---|---|---|---|

## Missing values
Values left NA, with reason.

| bank | fy | variable | reason |
|---|---|---|---|
