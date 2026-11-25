# Analysis spec: Impact of AI Adoption on Bank & Fintech Performance (India)

Fixed analysis spec (moved verbatim from CLAUDE.md, 2026-11-25). Do not change any specification because of
what results look like; log every change in `docs/spec_changes.md` with date and reason **before** re-running.

## 0. Current sprint (72 hours, full scope, CV deadline)
Goal: everything behind the three CV points: three-phase pipeline, 70+ verified events across
14 listed firms, dual-source dataset, FE + staggered DiD, six AI proxies, ROE / stock-return / PSU results.
Out of scope until after submission: mediation, GDELT media-tone control.
Gates: Day 1 end = clean financials + prices + keyword proxy, 30+ verified events.
Day 2 end = panel.parquet, final events file (70+ target), adoption dates for all panel banks, CAR tables.
Day 3 = FE + DiD + PSU interaction + robustness + figures.
Fallbacks: <50 verified events by Day 2 end -> report true count; a proxy's source fails -> drop it
and log in docs/spec_changes.md.

## 1. Research question
Does AI adoption improve the financial performance and market value of Indian banks,
and is the effect weaker for public sector (PSU) banks?

## 2. Three-phase pipeline
| Phase | Unit | Sample | Purpose |
|---|---|---|---|
| 1. Sector level | level × year: (a) whole sector (PSU + Private), (b) Private, (c) PSU | FY2011–FY2025 | Descriptive / motivating evidence only (~15 obs per level, not causal) |
| 2. Firm panel | bank × year | ~25 listed banks, FY2011–FY2026 | Main estimates: FE + staggered DiD |
| 3. Event study | AI announcement | 14 listed firms | Short-run market reaction (CARs) |

Fiscal year convention: FY2017 = 1 Apr 2016 to 31 Mar 2017. All dates stored as `YYYY-MM-DD`.

## 3. Samples
### 3a. Event-study firms (14, fixed)
- Private banks (5): HDFC Bank, ICICI Bank, Axis Bank, Kotak Mahindra Bank, IndusInd Bank
- PSU banks (4): SBI, Bank of Baroda, Punjab National Bank, Canara Bank
- NBFCs (2): Bajaj Finance, Bajaj Finserv
- Fintechs (3): One97 Communications (Paytm), PB Fintech, SBI Cards
- Qualitative case studies only (not in any regression): Razorpay, PhonePe

### 3b. Firm panel (banks only, ~25; NBFCs and fintechs are NOT in the panel)
Proposed list, to be confirmed by the user:
- PSU (12): SBI, Bank of Baroda, PNB, Canara, Union Bank of India, Bank of India, Indian Bank,
  Central Bank of India, Indian Overseas Bank, UCO Bank, Bank of Maharashtra, Punjab & Sind Bank
- Private (~13): HDFC, ICICI, Axis, Kotak, IndusInd, Federal, Yes Bank, RBL, Karur Vysya,
  City Union, South Indian, DCB, IDFC First (from FY2019 only, post-merger)
Unbalanced panel is fine. Stock-based variables start at listing date.

## 4. Variables
### Outcomes
- Primary: **ROE** = PAT / average equity × 100; **Annual stock return** = total return
  1 Apr to 31 Mar from adjusted close (no separate dividend add-on if adjusted close is used).
- Secondary: **ROA** = PAT / average total assets × 100; **Tobin's Q** = (market cap + total liabilities) / total assets.

### AI proxies (six)
Main:
1. `ai_kw` = AI-term count per 10,000 English words in annual report (FE model). AI terms are counted on the
   raw extracted text; the denominator counts only Latin-script tokens that pass the English-vocabulary filter
   plus a banking-jargon whitelist (legacy-font Hindi also extracts as Latin script; see docs/spec_changes.md).
   Report the share of Latin tokens dropped per report (English-only reports < 15%; flag > 40%).
   Robustness: `ai_kw_ln` = ln(1 + raw AI-term count), as in the source paper.
2. `post_adopt` = 1 from the FY of the bank's **first deployed AI system** (staggered DiD).
Robustness:
3. `ai_patents` = ln(1 + AI patent applications in year). Same search for ALL banks;
   no patent found = 0, never missing. Search: Google Patents / Indian Patent Office by assignee,
   AI classes (CPC G06N) plus AI keywords.
4. `ai_events_cum` = cumulative count of verified AI events up to FY end.
5. `fintech_idx` = Fintech index (Variables Selection sheet; Hamdouni 2025, IJFS 13(4):234): equal-weighted average (1/6 each) of
   (a) bank-wise mobile-banking transaction volume from RBI, min-max scaled 0–1 over all bank-FYs, and
   (b) feature dummies — mobile app, UPI live, chatbot, voice assistant, video-KYC — each 1 from the FY the
   feature went live. Report year coverage first; NA where the RBI volume is missing.
6. `ai_calls` = AI-term count per 10,000 words in earnings-call transcripts (BSE filings); FY22 onward only,
   run as a sub-period robustness check.
Patents source: Google Patents Public Datasets on BigQuery (free tier) or Google Patents search.

Keyword dictionary for `ai_kw` (case-insensitive except "AI"): artificial intelligence, machine learning,
deep learning, neural network, natural language processing, NLP, chatbot, conversational AI,
generative AI, GenAI, large language model, LLM, computer vision, robotic process automation, RPA,
predictive analytics, AI/ML, "AI" as a standalone uppercase token (regex `\bAI\b`, case-sensitive).
Exclude false positives (e.g., "Air India"). Store raw count, total words, and rate.
Also produce a **year-standardised** version (z-score within FY) to handle post-ChatGPT AI-washing.

### Adoption-date definitions (staggered DiD)
- Main: first deployed AI system (events sheet `Deployed = Y`, earliest date per bank).
- Alt 1: first AI event of any type (incl. MoUs / announcements).
- Alt 2: first FY where `ai_kw` exceeds a cutoff and stays above; two cutoffs: pooled median and pooled 75th percentile.

### Controls (all lagged one year)
ln(total assets), CAR (CRAR), loan-to-deposit ratio, liquidity ratio (liquid assets / total assets),
gross NPA ratio, `pca` (= 1 in bank-FYs under RBI Prompt Corrective Action; entry/exit dates built only
from RBI press releases, source URLs in docs/data_notes.md, never hardcoded from memory).
Not used as controls: firm age (collinear with firm + year FE; enters only as baseline age (FY2011) × AI and
as a DiD covariate), profit growth (mechanically tied to ROE; robustness only),
GDP and regulation (absorbed by year FE; GDP is used in Phase 1 only).

### Moderators / shocks
- Interactions with AI: PSU, COVID (FY2021), demonetisation (FY2017), post-ChatGPT (FY2023+),
  baseline firm age (age in FY2011), firm size, baseline Z-score.
- Baseline Z-score per bank = (mean ROA + mean equity/assets) / SD(ROA), over FY2011–FY2015, standardised
  across banks; NA for banks without FY2011–15 data (IDFC First).
- Firm-specific dummies: AQR clean-up FY2016–FY2018 × PSU; merger years
  (SBI associates FY2018, BoB FY2020, PNB / Canara / Union / Indian Bank FY2021, HDFC–HDFC Ltd FY2024,
  IDFC First FY2019), Yes Bank reconstruction FY2020.

### Mediators (deferred)
Cost-to-income ratio (efficiency channel), gross NPA ratio (credit channel).

## 5. Models
### Phase 1
Three levels: (a) whole sector = panel PSU + private banks combined, (b) private banks, (c) PSU banks.
Outcomes ROE, ROA, GNPA from RBI group aggregates (sector = PSU + private aggregates summed before ratios).
AI intensity = total-assets-weighted average of `ai_kw` across the panel banks in that level. Per level:
- trend chart of `ai_kw` vs ROE, ROA, GNPA, FY2011–FY2025;
- mean comparison pre-FY2017 (FY2011–FY2016) vs post-FY2017 (FY2017–FY2025);
- OLS: ROE_t on `ai_kw`_(t−1) + GDP growth + crisis dummies (demonetisation FY2017, AQR FY2016–FY2018,
  COVID FY2021); each regression also reported without the dummies, side by side.
Describe as descriptive evidence only.

### Phase 2a: Two-way FE (main for `ai_kw`)
Y_it = β·AI_i,t-1 + γ'X_i,t-1 + α_i + δ_t + ε_it
- R `fixest::feols`, SEs clustered by bank. With ~25 clusters, also report **wild cluster bootstrap**
  p-values (Webb weights).
- Heterogeneity: AI × PSU (the CV claim), plus the interactions listed above (incl. AI × baseline Z-score,
  AI × baseline age).
- Lags 0, 1 and 2 reported; lag 1 is the pre-specified main.

### Phase 2b: Staggered DiD (main for `post_adopt`)
- R `did::att_gt`, control group = not-yet-treated, `xformla = ~ baseline_age + baseline_ln_assets`.
- Report dynamic (event-time) aggregation with pre-trend coefficients, and the overall ATT.
- Robustness: `fixest::sunab` (Sun–Abraham); Alt 1 and Alt 2 adoption dates.

### Phase 3: Event study
- Market model, estimation window [−250, −30] trading days, minimum 120 valid days.
- Benchmark: Nifty 500 (main), Nifty Bank (robustness).
- CAR windows: [−1, +1] headline, [−5, +5].
- Tests: Kolari–Pynnönen adjusted BMP + Corrado rank test.
- Event date: first public announcement; after 15:30 IST → next trading day.
- Exclusions: earnings release within ±3 trading days; the firm's other event days are dropped from
  its estimation window; crisis windows: Paytm Payments Bank RBI action (from 2024-01-31),
  IndusInd derivative-accounting disclosure (Mar 2025), IL&FS crisis (Sep–Oct 2018, NBFC events),
  RBI embargo on Kotak digital onboarding / new cards (approx. 2024-04-24 to 2025-02-12),
  RBI ban on Bajaj Finance eCOM / Insta EMI lending (approx. 2023-11-15 to 2024-05-02).
  Verify these dates before use.
- Event clustering: Global Fintech Fest weeks and the Jan 2025 Microsoft India announcements put several
  firms' events on the same dates; this is why the Kolari–Pynnönen adjustment is used.
- Pre-listing events (SBI Cards before Mar 2020, Paytm / PB Fintech before Nov 2021) get no CAR;
  they still count for adoption history.
- Cross-section: CAR by bank type and event category.

### Robustness (run after core results)
Winsorise outcomes at 1/99; lagged profit growth as extra control; year-standardised `ai_kw`;
drop merger years.

## 6. Events data (`data/raw/events.csv`)
Columns: event_id, company, bank_type (Private/PSU/NBFC/Fintech), event_date (YYYY-MM-DD),
announce_time_ist, event_title, category, ai_technology, ai_specific (Y/N), deployed (Y/N),
source_primary, source_news, earnings_within_3d (Y/N), key_note, verified (Y/N).
Categories allowed: product/service launch, partnership/vendor deal, AI investment/acquisition,
internal deployment. Not allowed: awards, conference talks, executive interviews.
Every event needs a primary source (BSE/NSE filing, bank press release, or annual report) + a dated news source.
Only `verified = Y` events enter any analysis.

## 7. Data sources (free only)
- Bank financials: RBI *Statistical Tables Relating to Banks in India* (bank-wise, via DBIE).
  Check which years each ratio covers; fill gaps from annual reports and log each fill.
- Bank-group aggregates (Phase 1): same RBI publication.
- Prices: NSE/BSE historical data or yfinance (`.NS` tickers, adjusted close).
  Indices: Nifty 500 and Nifty Bank (niftyindices.com). Verify tickers before use.
- Annual reports: BSE corporate filings / bank investor-relations pages (PDF).
- Earnings dates: BSE corporate announcements (for the ±3-day screen).
- GDP: MOSPI / RBI DBIE.

## 8. Repo layout
```
data/raw/        untouched downloads (never edit)
data/interim/    cleaned pieces
data/final/      panel.parquet, events_clean.csv, ar_daily.parquet
src/python/      01_download_*.py, 02_clean_*.py, 03_ai_keywords.py, 04_build_panel.py
src/R/           10_phase1.R, 20_fe.R, 21_did.R, 30_event_study.R, 40_robustness.R
results/tables/  results/figures/  results/spec_log.md
docs/            spec_changes.md, data_notes.md
```
Language split: Python for downloading, PDF parsing (pymupdf / pdfplumber), text mining, panel
assembly; R for estimation (fixest, did).

