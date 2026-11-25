# CLAUDE.md: Impact of AI Adoption on Bank & Fintech Performance (India)

Research project under Prof. Paras Sachdeva, DMS IIT Delhi: does AI adoption improve the financial performance
and market value of Indian banks, and is the effect weaker for public sector (PSU) banks?

**Full spec in `docs/spec.md` - read only the section needed for the current task.**
Do not change the spec because of what results look like; log every change in `docs/spec_changes.md`
(date + reason) **before** re-running.

## 9. Version control (local git repo in this folder = source of truth)
- Setup: local folder synced with a PUBLIC GitHub repo (remote `origin`). If not yet a repo:
  `git init`, `git remote add origin <url>`, first commit, `git push -u origin main`.
- At the start of every session: `git pull` before touching any file.
- After every task: commit and `git push`, so local and GitHub stay identical.
- The repo is public: before every commit, check that no secrets, credentials, or large raw PDFs are staged.
- Commit after every completed task with a descriptive message (e.g. "Add RBI financials cleaner, 25 banks FY11-26").
  If a remote (e.g. private GitHub) is configured, also `git push`. Never leave work uncommitted at the end of a session.
- Commit: code, CLAUDE.md, docs/, data/raw/events.csv, data/final/ small files (<50 MB), results/.
- Do NOT commit: annual-report PDFs, raw price dumps or other large raw downloads (list them in .gitignore;
  keep them in local data/raw/ and a Drive backup). Record each download's source URL and date in docs/data_notes.md
  so it can be re-downloaded.
- Never commit secrets (API keys, tokens, BigQuery credentials); keep them in a .env file that is gitignored.
- Tag milestones: `git tag day1-data`, `day2-panel`, `day3-results`.

## 10. Working rules for Claude Code
- Never hand-edit files in `data/raw/`. Every transformation is a script.
- After every merge, assert row counts and key uniqueness (bank_id × fy). Print merge diagnostics.
- Log every estimated specification in `results/spec_log.md`, including null results.
- Report all pre-specified outcomes and proxies, not just significant ones.
- Report units explicitly: percentage points vs percent; per 1 SD of `ai_kw` or for `post_adopt` = 1.
- Do not invent data. If a value is missing, leave it NA and log it in `docs/data_notes.md`.
- Write scripts; do not run long jobs (downloads, PDF parsing, transcripts) yourself - tell the user the exact
  command to run. Scripts print a summary of at most 20 lines and write details to logs/. Never open PDFs, parquet
  or large CSVs directly; use head or a shape/columns check only. Do not self-review or summarise past work unless asked.
