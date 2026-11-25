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

## Prices: checks and flags (2026-11-25)
- Listing-date starts in the Yahoo series: PSB 2010-12-30, IDFC First 2015-11-06 (IDFC Bank listing; panel uses FY2019+ only), RBL 2016-08-31, SBI Cards 2020-03-16, PB Fintech 2021-11-15, Paytm 2021-11-18.
- Corporate actions recorded by Yahoo (adjusted close accounts for them): HDFC 2011, 2019, 2025-08-26 (1:1 bonus); Kotak 2010, 2015, 2026-01-14; SBI 2014; Canara 2024; Bajaj Finance 2016, 2025; and others (see `splits` column in raw files).
- Download-day bar dropped as possibly incomplete. 2026-11-24 missing in all series (market holiday).
- 14 daily moves with |return| > 30% are listed in `data/interim/price_flags_extreme.csv`; `returns_fy.csv` carries `n_extreme_days` per firm-FY.
  - Genuine market moves: PSU recapitalisation rally 2017-10-25 (BOB, BOI, Canara, PNB, Union); IndusInd 2020-03-26; Yes Bank 2019-10-03 and March 2020 reconstruction; PB Fintech 2026-09-24 (−36% on 27M shares, cause still to be checked; falls inside the event-study period).
  - **Suspect data: Karur Vysya 2011-05-04 (+30%).** Pre-May-2011 bars have very low volume and prices that look scaled differently; likely an unadjusted corporate action in Yahoo. Affects KVB FY2012 return. Cross-check against NSE bhavcopy before use.
- Fiscal-year total return (`stock_ret_pct`, percent) = last adjusted close of FY / last adjusted close of prior FY − 1. Set to NA if the firm was not trading by the start of the FY. Coverage FY2010–FY2026.

## Gap fills
Values filled from annual reports where RBI tables lack coverage.

| bank | fy | variable | value | source | note |
|---|---|---|---|---|---|

## Missing values
Values left NA, with reason.

| bank | fy | variable | reason |
|---|---|---|---|
