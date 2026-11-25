"""Market capitalisation and Tobin's Q per panel bank at each FY end (31 March).

shares = paid-up capital (RBI Table 1, Rs crore) / face value
market cap (Rs crore) = actual FY-end close x shares
tobins_q = (market cap + total liabilities excluding equity) / total assets
"""
import sys

import numpy as np
import pandas as pd
import yfinance as yf

from config import FACE_VALUE_NOW, FIRMS, FV_SPLITS, INTERIM, PREF_CAPITAL, RAW

TOL = 0.05
CHECK_BANKS = ["SBI", "ICICI", "AXIS", "PNB", "BOB"]  # no splits/bonuses since March 2025
tickers = {f[0]: f[3] for f in FIRMS}

fin = pd.read_csv(INTERIM / "rbi_bank_financials.csv",
                  usecols=["bank_id", "fy", "capital", "reserves", "total_assets"])
rows = []
for bank_id in FACE_VALUE_NOW:
    px = pd.read_csv(RAW / "prices" / f"{bank_id}.csv", parse_dates=["date"])
    splits = px.loc[px["splits"] > 0, ["date", "splits"]]
    yahoo_fv = {d.strftime("%Y-%m-%d"): f for d, f in zip(splits["date"], splits["splits"])}
    for d, f in FV_SPLITS.get(bank_id, {}).items():
        assert d in yahoo_fv and abs(yahoo_fv[d] - f) < 1e-9, f"{bank_id} FV split {d} not in Yahoo split records"
    px["fy"] = px["date"].dt.year + (px["date"].dt.month >= 4).astype(int)
    fy_end = px.groupby("fy").tail(1)
    for r in fy_end.itertuples():
        if r.date < pd.Timestamp(f"{r.fy}-03-24"):  # FY not complete in the price data
            continue
        later = splits[splits["date"] > r.date]
        unadj = float(np.prod(later["splits"])) if len(later) else 1.0  # Yahoo close is split/bonus adjusted
        fv_later = [f for d, f in FV_SPLITS.get(bank_id, {}).items() if pd.Timestamp(d) > r.date]
        face_value = FACE_VALUE_NOW[bank_id] * float(np.prod(fv_later)) if fv_later else FACE_VALUE_NOW[bank_id]
        rows.append({"bank_id": bank_id, "fy": r.fy, "fy_end_date": r.date.strftime("%Y-%m-%d"),
                     "close_yahoo": r.close, "unadj_factor": unadj, "close_actual": r.close * unadj,
                     "face_value": face_value})
mc = pd.DataFrame(rows)
n0 = len(mc)
mc = mc.merge(fin, on=["bank_id", "fy"], how="left", validate="one_to_one")
assert len(mc) == n0 and not mc.duplicated(["bank_id", "fy"]).any()
print(f"merge prices x RBI: {n0} rows, with capital: {mc.capital.notna().sum()}")

mc["pref_capital_flag"] = ""
for b, (lo, hi, note) in PREF_CAPITAL.items():
    mc.loc[(mc.bank_id == b) & mc.fy.between(lo, hi), "pref_capital_flag"] = note
pref = mc["pref_capital_flag"] != ""
mc["shares_cr"] = mc["capital"] / mc["face_value"]  # crore shares (capital in Rs crore / Rs per share)
mc.loc[pref, "shares_cr"] = np.nan  # capital includes preference shares: equity share count unknown
mc["market_cap_cr"] = mc["close_actual"] * mc["shares_cr"]
mc["equity"] = mc["capital"] + mc["reserves"]
mc["liab_ex_equity"] = mc["total_assets"] - mc["equity"]
mc["tobins_q"] = (mc["market_cap_cr"] + mc["liab_ex_equity"]) / mc["total_assets"]
mc = mc.sort_values(["bank_id", "fy"])
mc["shares_ratio_yoy"] = mc.groupby("bank_id")["shares_cr"].pct_change(fill_method=None) + 1

cols = ["bank_id", "fy", "fy_end_date", "close_yahoo", "unadj_factor", "close_actual", "face_value", "capital",
        "shares_cr", "market_cap_cr", "total_assets", "equity", "liab_ex_equity", "tobins_q", "shares_ratio_yoy",
        "pref_capital_flag"]
mc = mc[cols]
mc.to_csv(INTERIM / "market_cap_fy.csv", index=False)

# ---- diagnostics ----
print(f"\nbank-years set to NA (capital includes preference shares): {pref.sum()}")
print("market cap continuity across split dates (FY-end mcap ratio should be near the FY price return, not x5/x10):")
mc["mcap_ratio_yoy"] = mc.groupby("bank_id")["market_cap_cr"].pct_change(fill_method=None) + 1
mc["price_ratio_yoy"] = mc.groupby("bank_id")["close_actual"].pct_change(fill_method=None) + 1
for b, ev in FV_SPLITS.items():
    for d, f in ev.items():
        fy = pd.Timestamp(d).year + (pd.Timestamp(d).month >= 4)
        s = mc[(mc.bank_id == b) & (mc.fy == fy)]
        if len(s) and pd.notna(s.mcap_ratio_yoy.iloc[0]):
            print(f"  {b:8s} FY{fy} split x{f}: mcap ratio {s.mcap_ratio_yoy.iloc[0]:.2f}, "
                  f"actual price ratio {s.price_ratio_yoy.iloc[0]:.3f} (price falls by split factor)")
print("\nFace-value split years: implied share count jumps by the split factor (capital unchanged):")
for b, ev in FV_SPLITS.items():
    for d, f in ev.items():
        fy = pd.Timestamp(d).year + (pd.Timestamp(d).month >= 4)
        s = mc[(mc.bank_id == b) & mc.fy.between(fy - 1, fy)][["fy", "shares_cr", "shares_ratio_yoy"]]
        print(f"  {b:8s} split {d} x{f}: " + "; ".join(f"FY{int(x.fy)} {x.shares_cr:,.1f}cr ({x.shares_ratio_yoy:.2f})"
                                                       for x in s.itertuples() if pd.notna(x.shares_cr)))
big = mc[(mc.shares_ratio_yoy > 1.5) | (mc.shares_ratio_yoy < 0.67)]
print("\nLarge YoY share-count changes (|ratio| outside 0.67-1.5; expected for recapitalisation, mergers, bonuses):")
print(big[["bank_id", "fy", "capital", "face_value", "shares_cr", "shares_ratio_yoy"]].round(2).to_string(index=False))
print("\nTobin's Q summary by FY:")
print(mc.groupby("fy")["tobins_q"].describe()[["count", "mean", "min", "max"]].round(3).to_string())

print("\nCross-check vs yfinance current market cap (latest close x FY2025 paid-up capital / current face value):")
ok = True
for b in CHECK_BANKS:
    px = pd.read_csv(RAW / "prices" / f"{b}.csv")
    last_close = px["close"].iloc[-1]
    cap25 = fin.loc[(fin.bank_id == b) & (fin.fy == 2025), "capital"].iloc[0]
    ours = last_close * cap25 / FACE_VALUE_NOW[b]  # Rs crore
    info = yf.Ticker(tickers[b]).fast_info
    yfc = info["market_cap"] / 1e7
    diff = ours / yfc - 1
    ok &= abs(diff) <= TOL
    print(f"  {b:6s} ours Rs {ours:12,.0f} cr | yfinance Rs {yfc:12,.0f} cr | diff {diff:+.2%} | "
          f"{'OK' if abs(diff) <= TOL else 'FAIL'}")
if not ok:
    sys.exit("market cap cross-check FAILED (> 5%)")
print("cross-check passed (all within 5%)")
