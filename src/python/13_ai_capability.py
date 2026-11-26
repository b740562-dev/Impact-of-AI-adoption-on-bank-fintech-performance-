"""ai_capability (proxy 3, replaces ai_patents; docs/spec_changes.md 2026-11-26): sum of four binary annual-report mentions.

Reuses the extracted annual-report text in data/interim/ar_text/ (written by 03_ai_keywords.py; no PDFs opened).
Per bank x FY, 1 if that FY's report mentions the component, else 0; as observed per report (no carry-forward);
bank-FYs without a report are absent here and NA in the panel.
  cap_lead       dedicated digital / data / AI leader (Chief Digital/Data/Analytics/AI Officer; Head of AI/Analytics/
                 Data Science). CIO, CTO, CISO are not in the patterns.
  cap_lab        AI / analytics / data / innovation lab or centre of excellence
  cap_committee  board or management committee for digital / AI / data / innovation (IT Strategy, risk, audit excluded)
  cap_team       in-house data science / AI / ML / analytics team
Output data/interim/ai_capability.parquet; snippets (<= 3 per bank x component) in logs/ai_capability_snippets.csv.
Matching is case-insensitive except the acronyms AI and ML.
"""
import re

import pandas as pd

from config import FIRMS, INTERIM, RAW

ROOT = RAW.parent.parent
TXT = INTERIM / "ar_text"
TYPES = {f[0]: f[2] for f in FIRMS}

AI_ = (r"(?:(?-i:AI)(?:\s*(?:/|&|-|and)\s*(?-i:ML))?|(?-i:Gen\s?AI)|generative\s+(?-i:AI)|artificial\s+intelligence"
       r"|machine\s+learning|(?-i:ML))")
ANA = r"(?:analytics|data\s+science|data\s+analytics|advanced\s+analytics|business\s+analytics|big\s+data)"
# committee qualifier and the words allowed between it and "Committee"
CQ = r"(?:[Dd]igital|[Dd]ata|[Aa]nalytics|[Ii]nnovation|(?-i:AI)|[Aa]rtificial\s+[Ii]ntelligence|(?-i:Gen\s?AI)|[Mm]achine\s+[Ll]earning)"
TAIL = (r"(?:[Tt]ransformation|[Bb]anking|[Ss]trategy|[Ii]nitiatives|[Pp]ayments|[Gg]overnance|[Ss]teering|[Pp]roducts?|"
        r"[Cc]hannels?|[Bb]usiness|[Aa]doption|[Oo]versight|[Rr]eview|[Mm]onitoring|[Mm]anagement|[Ii]mplementation|"
        r"[Dd]elivery|[Ee]xecutive|[Aa]dvisory|[Tt]echnology|[Pp]latforms?|[Ss]olutions|[Ss]ervices|[Ll]ending|"
        r"[Ii]nnovation|[Aa]nalytics|[Dd]ata|[Dd]igital|[Ee]cosystem|[Ee]ngagement|[Cc]ouncil)")

PATTERNS = {
    "lead": [
        r"\bchief\s+(?:digital|data|analytics|artificial\s+intelligence|(?-i:AI))"
        r"(?:\s+(?:and|&)\s+\w+|\s+transformation|\s+banking|\s+management)?\s+officers?\b",
        rf"\bhead\b\s*(?:of|for|[-–—:,(])?\s*(?:the\s+)?(?:{AI_}|{ANA})\b",
        rf"\b(?:{AI_}|{ANA})\s+head\b",
    ],
    "lab": [
        rf"\b(?:{AI_}|{ANA}|data|innovation)\s+(?:labs?|laborator(?:y|ies))\b",
        rf"\b(?:{AI_}|{ANA}|data|innovation)\s+(?:centres?|centers?)\s+of\s+excellence\b",
        rf"\b(?:centres?|centers?)\s+of\s+excellence\s+(?:\(\s*CoE\s*\)\s+)?(?:for|in|on)\s+(?:the\s+)?(?:\w+\s+){{0,2}}?"
        rf"(?:{AI_}|{ANA}|innovation)\b",
        rf"\b(?:{AI_}|{ANA}|data|innovation)\s+(?-i:CoE|COE)s?\b",
    ],
    "committee": [
        rf"(?-i:\b(?:[A-Z][\w-]*\s+){{0,2}}{CQ}(?:\s+(?:and|&)\s+(?:{CQ}|[A-Z][\w-]*))?(?:\s+{TAIL})*\s+[Cc]ommittee)\b",
        rf"(?-i:\b[Cc]ommittee\s+(?:of\s+(?:the\s+)?Board\s+|of\s+Executives\s+)?(?:on|for)\s+(?:the\s+)?{CQ}"
        rf"(?:\s+(?:{TAIL}|and|&))*)\b",
    ],
    "team": [
        r"\bdata\s+scientists?\b",
        rf"\b(?:{AI_}|{ANA}|data)\s+(?:teams?|units?|cells?|verticals?|divisions?|departments?)\b",
        rf"\b(?:teams?|units?|cells?|pool)\s+of\s+(?:\w+\s+){{0,2}}?(?:data\s+engineers|(?:{AI_}|{ANA})\s+"
        rf"(?:experts|specialists|engineers|professionals))\b",
    ],
}
REGEX = {k: re.compile("(?i)" + "|".join(f"(?:{p})" for p in v)) for k, v in PATTERNS.items()}
# exclusions on the match plus the next 40 characters
EXCL = {
    "committee": re.compile(r"(?i)\b(?:risk|audit|fraud|security|vigilance)\b|(?-i:\bIT\s+Strategy)|information\s+technology\s+strategy"),
    "lead": re.compile(r"(?i)\bhead\s*(?:of|for|[-–—:,(])?\s*(?:the\s+)?data\s+(?:centre|center|protection|privacy|security)"),
    "team": re.compile(r"(?i)\bdata\s+(?:centre|center|entry|protection|privacy|security)"),
}
# context exclusions (decided after reading the first snippet file; logged in docs/data_notes.md)
BIO = re.compile(r"(?i)\b(?:prior\s+to|previously|formerly|former|erstwhile|served\s+as|in\s+(?:his|her)\s+role|"
                 r"(?:he|she)\s+(?:was|is|has|had|leads|led|served|heads|headed))\b")  # past/external roles, same sentence
CSR = re.compile(r"(?i)\b(?:students?|schools?|CSR|children|colleges?|universit(?:y|ies)|tinkering)\b")  # lab, +-150 chars
EXTERNAL = re.compile(r"(?i)\b(?:IBA|RBI|Reserve\s+Bank|Government|GoI|Ministry|EASE|NITI)\b")  # committee, 60 chars before
SETUP_BY = re.compile(r"(?i)^.{0,60}?set\s+up\s+by\s+(?:the\s+)?(?:Ministry|Government|Reserve\s+Bank|RBI|IBA)")
IT_PREFIX = re.compile(r"(?:\bIT|Information\s+Technology)\s+(?:and|&)\s*$")  # "IT and Digital Strategy Committee"
DOMAIN = re.compile(r"(?i)\b(?:treasury|portfolio|risk|market|HR|human\s+resources?|performance\s+and|financial)\s*$")


def excluded(comp, text, m):
    s, e = m.start(), m.end()
    if comp in EXCL and EXCL[comp].search(text[s:e + 40]):
        return True
    pre = text[max(0, s - 150):s]
    sent_pre = pre[pre.rfind(". ") + 1:]
    if BIO.search(sent_pre):
        return True
    if comp == "lab" and CSR.search(text[max(0, s - 150):e + 150]):
        return True
    if comp == "committee" and (EXTERNAL.search(text[max(0, s - 60):s]) or SETUP_BY.search(text[e:e + 120])
                                or IT_PREFIX.search(text[max(0, s - 30):s])):
        return True
    if comp == "team" and DOMAIN.search(text[max(0, s - 25):s]):  # e.g. "Treasury Analytics unit"
        return True
    return False


def sentence(text, s, e, width=350):
    a = max(text.rfind(". ", 0, s), text.rfind("? ", 0, s), text.rfind("! ", 0, s)) + 2
    b = min([i for i in (text.find(". ", e), text.find("? ", e), text.find("! ", e)) if i != -1] or [len(text)]) + 1
    a, b = max(a, s - width // 2), min(b, e + width // 2)
    return text[a:b].strip()


rows, snips = [], []
for f in sorted(TXT.glob("*_FY*.txt")):
    bank, fy = f.stem.rsplit("_FY", 1)
    text = f.read_text(encoding="utf-8").split("\n", 1)[-1]
    row = {"bank_id": bank, "fy": int(fy)}
    for comp, rx in REGEX.items():
        hits = [m for m in rx.finditer(text) if not excluded(comp, text, m)]
        row[f"cap_{comp}"] = int(bool(hits))
        row[f"n_{comp}"] = len(hits)
        snips += [{"bank_id": bank, "fy": int(fy), "component": comp, "match": m.group(0),
                   "sentence": sentence(text, m.start(), m.end())} for m in hits[:1]]
    rows.append(row)

out = pd.DataFrame(rows)
assert not out.duplicated(["bank_id", "fy"]).any()
comps = [f"cap_{c}" for c in PATTERNS]
out["ai_capability"] = out[comps].sum(axis=1)
out["bank_type"] = out["bank_id"].map(TYPES)
out.to_parquet(INTERIM / "ai_capability.parquet", index=False)

# snippets: up to 3 per bank x component (earliest, middle, latest FY with a match) for manual checking
sn = pd.DataFrame(snips).sort_values(["bank_id", "component", "fy"]).reset_index(drop=True)
g = sn.groupby(["bank_id", "component"])
k, n = g.cumcount(), g["fy"].transform("size")
pick = sn[(k == 0) | (k == n // 2) | (k == n - 1)]
(ROOT / "logs").mkdir(exist_ok=True)
pick[["bank_id", "fy", "component", "match", "sentence"]].to_csv(ROOT / "logs" / "ai_capability_snippets.csv", index=False)

short = {"cap_lead": "lead", "cap_lab": "lab", "cap_committee": "comm", "cap_team": "team"}
t = out.assign(t=out["bank_type"].map({"PSU": "PSU", "Private": "Pvt"})).pivot_table(
    index="fy", columns="t", values=comps, aggfunc="mean")
t.columns = [f"{short[c]}_{ty}" for c, ty in t.columns]
print(f"share of 1s by FY and bank type ({len(out)} reports, {out.bank_id.nunique()} banks):")
print(t.round(2).to_string())
by = out.groupby("bank_type")[comps + ["ai_capability"]].mean().round(2).rename(columns=short)
print("all FYs: " + "; ".join(f"{i}: " + ", ".join(f"{c} {v}" for c, v in r.items()) for i, r in by.iterrows()))
print(f"snippets: {len(pick)} rows -> logs/ai_capability_snippets.csv")
