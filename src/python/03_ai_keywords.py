"""AI keyword intensity in bank annual reports: ai_kw = AI-term count per 10,000 English words.

English words = tokens that occur in >= VOCAB_MIN_DOCS different private-bank reports (English-only), so that
legacy-font Hindi pages (extracted as Latin gibberish) in bilingual PSU reports do not inflate the denominator.
"""
import collections
import random
import sys

import numpy as np
import pandas as pd
import pymupdf

from ai_terms import TERMS, WORD, iter_matches, normalise
from config import FIRMS, INTERIM, RAW

AR = RAW / "annual_reports"
TXT = INTERIM / "ar_text"
TXT.mkdir(parents=True, exist_ok=True)
LOW_WORDS_PER_PAGE = 50  # English words per page below this: scanned / Hindi-only file -> NA
VOCAB_MIN_DOCS = 3
PRIVATE = {f[0] for f in FIRMS if f[2] == "Private"}


def load_text(bank_id, fy, pdf):
    """Cached extraction; header line = 'pages|pdf_bytes' so a replaced PDF is re-extracted."""
    cache = TXT / f"{bank_id}_FY{fy}.txt"
    size = pdf.stat().st_size
    if cache.exists():
        head, text = cache.read_text(encoding="utf-8").split("\n", 1)
        parts = head.split("|")
        if len(parts) == 2 and int(parts[1]) == size:
            return int(parts[0]), text
    with pymupdf.open(pdf) as doc:
        pages = len(doc)
        text = normalise("\n".join(p.get_text("text") for p in doc))
    cache.write_text(f"{pages}|{size}\n{text}", encoding="utf-8")
    return pages, text


idx = pd.read_csv(AR / "_index.csv")
sel = idx[idx["selected"]]
docs, errors = {}, []
for r in sel.itertuples():
    pdf = AR / r.file
    if not pdf.exists():
        errors.append((r.bank_id, r.fy, "missing PDF"))
        continue
    try:
        docs[(r.bank_id, r.fy)] = load_text(r.bank_id, r.fy, pdf)
    except Exception as e:  # corrupt PDF: leave NA
        errors.append((r.bank_id, r.fy, f"{type(e).__name__}: {e}"[:100]))

df_count = collections.Counter()
for (b, fy), (_, text) in docs.items():
    if b in PRIVATE:
        df_count.update({w.lower() for w in WORD.findall(text)})
vocab = {w for w, n in df_count.items() if n >= VOCAB_MIN_DOCS}
print(f"reports loaded: {len(docs)}  English vocabulary (>= {VOCAB_MIN_DOCS} private-bank reports): {len(vocab):,} words")

rows, snippets = [], collections.defaultdict(list)
for (b, fy), (pages, text) in sorted(docs.items()):
    counts = dict.fromkeys([k for k, _ in TERMS], 0)
    for m, clean in iter_matches(text):
        counts[m.lastgroup] += 1
        snippets[b].append((fy, m.lastgroup, clean[max(m.start() - 70, 0): m.end() + 70]))
    tokens = WORD.findall(text)
    english = sum(1 for w in tokens if w.lower() in vocab)
    rows.append({"bank_id": b, "fy": fy, "pages": pages, "tokens_raw": len(tokens), "total_words": english,
                 "ai_kw_count": sum(counts.values()), **{f"n_{k}": v for k, v in counts.items()}})

kw = pd.DataFrame(rows)
assert not kw.duplicated(["bank_id", "fy"]).any()
kw["english_share"] = kw["total_words"] / kw["tokens_raw"]
kw["low_text"] = np.where(kw["total_words"] < LOW_WORDS_PER_PAGE * kw["pages"], "Y", "N")
kw["ai_kw"] = np.where(kw["low_text"] == "N", kw["ai_kw_count"] / kw["total_words"] * 10_000, np.nan)
g = kw.groupby("fy")["ai_kw"]
kw["ai_kw_z"] = (kw["ai_kw"] - g.transform("mean")) / g.transform("std")
kw = kw.sort_values(["bank_id", "fy"])
kw.to_csv(INTERIM / "ai_kw.csv", index=False)
kw.to_parquet(INTERIM / "ai_keywords.parquet", index=False)

rng = random.Random(20261125)
snip = [{"bank_id": b, "fy": fy, "term": t, "context": c}
        for b, lst in sorted(snippets.items()) for fy, t, c in rng.sample(lst, min(5, len(lst)))]
pd.DataFrame(snip).to_csv(INTERIM / "ai_kw_snippets.csv", index=False)

# ---- diagnostics ----
print(f"reports counted: {len(kw)}  load errors: {errors}")
print("low-text (NA):", kw.loc[kw.low_text == "Y", ["bank_id", "fy", "pages", "total_words"]].to_dict("records"))
psu = {f[0] for f in FIRMS if f[2] == "PSU"}
print("median English share of tokens: PSU", kw[kw.bank_id.isin(psu)].english_share.median().round(3),
      "| Private", kw[kw.bank_id.isin(PRIVATE)].english_share.median().round(3))
print("\nai_kw (per 10,000 English words) by FY:")
print(kw.groupby("fy")["ai_kw"].describe()[["count", "mean", "50%", "max"]].round(2).to_string())
print("\nterm totals:", kw[[f"n_{k}" for k, _ in TERMS]].sum().sort_values(ascending=False).to_dict())
cols = ["bank_id", "fy", "ai_kw", "ai_kw_count", "total_words"]
print("\n10 highest bank-years:\n", kw.nlargest(10, "ai_kw")[cols].round(2).to_string(index=False))
print("\n10 lowest bank-years (FY2020+):\n",
      kw[kw.fy >= 2020].nsmallest(10, "ai_kw")[cols].round(2).to_string(index=False))
print("\n5 random matched snippets per bank (all in data/interim/ai_kw_snippets.csv):")
for s in snip:
    print(f"  {s['bank_id']:9s} FY{s['fy']} {s['term']:22s} ...{s['context']}...")
if "--grid" in sys.argv:
    print(kw.pivot(index="bank_id", columns="fy", values="ai_kw").round(1).to_string())
