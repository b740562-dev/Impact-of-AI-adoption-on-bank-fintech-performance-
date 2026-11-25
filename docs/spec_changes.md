# Spec changes

Changes to the fixed spec in CLAUDE.md. Each entry: date, section, change, reason. Logged **before** re-running.

| Date | Section | Change | Reason |
|---|---|---|---|
| 2026-11-25 | §4 `ai_kw` dictionary | Acronyms LLM/LLMs, NLP and RPA are matched case-sensitively (uppercase as written, "LLMS" all-caps excluded) and only where the ±60-character window contains ordinary lowercase text; "LLM" in law-degree context (LLB/LL.M/Master of Law) is excluded. Full-phrase terms stay case-insensitive. | Audit of matches before any results: "LLMS" = Loan Lifecycle Management System (BoM, SBI, Central), "LLM" = directors' law degree, and legacy-font Hindi (Kruti Dev–style) renders as Latin gibberish producing isolated "LLM"/"Rpa"/"llm" tokens (e.g. PNB FY2015: 100 false "LLM"). Implements the spec's "exclude false positives". |
| 2026-11-25 | §4 `ai_kw` denominator | "Total words" = English words only: tokens that occur in at least 3 different private-bank annual reports (English-only reports). Raw token count is also stored. | Bilingual PSU reports set in legacy Hindi fonts extract as Latin gibberish, which inflated the word count of PSU reports and would bias PSU `ai_kw` downward. |
| 2026-11-25 | §2, §3b, §4 (sample period) | Accounting outcomes (ROE, ROA, controls) end FY2025 because RBI FY2026 tables are not yet published; stock returns run to FY2026. | RBI *Statistical Tables Relating to Banks in India* on DBIE covers FY2005–FY2025 as of 2026-11-25; the 2025-26 edition is not yet released. |
