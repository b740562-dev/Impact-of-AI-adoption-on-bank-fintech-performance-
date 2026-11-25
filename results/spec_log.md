# Specification log

Every estimated specification, including null results.

| Date | Script | Outcome | AI proxy | Sample | Controls / FE | Estimate (units) | SE / p | Note |
|---|---|---|---|---|---|---|---|---|
| 2026-11-26 | src/R/10_phase1.R | ROE (%) | assets-weighted `ai_kw` (t−1) | Sector, FY2012–25, n=14 | GDP growth | +2.166 pp ROE per 1 AI term / 10k words | SE 3.07, p=0.495 | Phase 1, descriptive; conventional SEs |
| 2026-11-26 | src/R/10_phase1.R | ROE (%) | assets-weighted `ai_kw` (t−1) | Sector, FY2012–25, n=14 | GDP growth + demonetisation, AQR, COVID | −0.841 pp | SE 3.12, p=0.794 | Phase 1, descriptive |
| 2026-11-26 | src/R/10_phase1.R | ROE (%) | assets-weighted `ai_kw` (t−1) | Private, FY2012–25, n=14 | GDP growth | −1.488 pp | SE 1.36, p=0.298 | Phase 1, descriptive |
| 2026-11-26 | src/R/10_phase1.R | ROE (%) | assets-weighted `ai_kw` (t−1) | Private, FY2012–25, n=14 | GDP growth + demonetisation, AQR, COVID | −2.725 pp | SE 1.51, p=0.109 | Phase 1, descriptive |
| 2026-11-26 | src/R/10_phase1.R | ROE (%) | assets-weighted `ai_kw` (t−1) | PSU, FY2012–25, n=14 | GDP growth | +5.002 pp | SE 4.60, p=0.301 | Phase 1, descriptive |
| 2026-11-26 | src/R/10_phase1.R | ROE (%) | assets-weighted `ai_kw` (t−1) | PSU, FY2012–25, n=14 | GDP growth + demonetisation, AQR, COVID | +0.930 pp | SE 4.54, p=0.843 | Phase 1, descriptive |
| 2026-11-26 | src/R/10_phase1.R | `ai_kw`, ROE, ROA, GNPA | — | 3 levels, pre FY2011–16 (n=6) vs post FY2017–25 (n=9) | Welch t-test | see results/tables/phase1_prepost.csv | — | Phase 1 mean comparison, descriptive |
