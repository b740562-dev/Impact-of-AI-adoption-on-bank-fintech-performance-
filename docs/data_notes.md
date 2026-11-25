# Data notes

## Downloads log
Every raw download: file, source URL, date downloaded, notes. Large raw files are gitignored; this log is how to re-create them.

| File / folder | Source URL | Downloaded | Notes |
|---|---|---|---|
| data/raw/prices/*.csv (30 firms + 2 indices) | Yahoo Finance via `yfinance` (`src/python/01_download_prices.py`), tickers in `src/python/config.py` | 2026-11-25 | Daily OHLC, close, adjusted close (splits + dividends), volume, 2009-01-02 onward. Gitignored; re-run the script to rebuild. Indices: Nifty 500 = `^CRSLDX`, Nifty Bank = `^NSEBANK` (Yahoo, used in place of niftyindices.com for now; cross-check pending). |

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
