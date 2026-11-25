# Phase 1 (CLAUDE.md §5): descriptive sector-level evidence, three levels (Sector, Private, PSU), FY2011-FY2025.
# Input: data/interim/phase1_levels.csv (src/python/04_build_phase1.py). Run from the project root:
#   Rscript src/R/10_phase1.R
# Outputs: results/figures/phase1_trends_<level>.png, results/tables/phase1_prepost.csv,
#          results/tables/phase1_ols.{csv,md}. Descriptive evidence only (about 14 observations per level).
suppressPackageStartupMessages({
  library(data.table); library(ggplot2); library(modelsummary)
})

d <- fread("data/interim/phase1_levels.csv")
stopifnot(!anyDuplicated(d[, .(level, fy)]))
if (all(is.na(d$gdp_growth))) stop("gdp_growth missing: add data/interim/gdp_growth.csv and rebuild phase1_levels.csv")
dir.create("results/figures", showWarnings = FALSE, recursive = TRUE)
dir.create("results/tables", showWarnings = FALSE, recursive = TRUE)
levels_order <- c("Sector", "Private", "PSU")

# 1. Trend charts: ai_kw (assets-weighted) vs ROE, ROA, GNPA, each outcome against ai_kw on a second axis
for (lv in levels_order) {
  x <- d[level == lv]
  long <- melt(x, id.vars = c("fy", "ai_kw_w"), measure.vars = c("roe", "roa", "gnpa_ratio"),
               variable.name = "outcome", value.name = "value")
  long[, outcome := factor(outcome, c("roe", "roa", "gnpa_ratio"), c("ROE (%)", "ROA (%)", "Gross NPA ratio (%)"))]
  scale_k <- long[, .(k = max(abs(value), na.rm = TRUE) / max(ai_kw_w, 0.01, na.rm = TRUE)), by = outcome]
  long <- merge(long, scale_k, by = "outcome")
  p <- ggplot(long, aes(fy)) +
    geom_col(aes(y = ai_kw_w * k), fill = "grey80", width = 0.7) +
    geom_line(aes(y = value), linewidth = 0.8) + geom_point(aes(y = value), size = 1.4) +
    geom_vline(xintercept = 2016.5, linetype = "dashed") +
    facet_wrap(~outcome, ncol = 1, scales = "free_y") +
    labs(title = sprintf("Phase 1 (%s): AI keyword intensity and performance, FY2011-FY2025", lv),
         subtitle = "Bars: assets-weighted ai_kw (AI terms per 10,000 English words, rescaled per panel); line: outcome",
         x = "Fiscal year", y = NULL, caption = "Descriptive evidence only. Dashed line: FY2017.") +
    theme_minimal(base_size = 10)
  ggsave(sprintf("results/figures/phase1_trends_%s.png", tolower(lv)), p, width = 7, height = 7, dpi = 200)
}

# 2. Pre-FY2017 (FY2011-16) vs post (FY2017-25) means, Welch t-test
vars <- c("ai_kw_w", "roe", "roa", "gnpa_ratio")
pp <- rbindlist(lapply(levels_order, function(lv) rbindlist(lapply(vars, function(v) {
  pre <- d[level == lv & post_fy2017 == 0][[v]]; post <- d[level == lv & post_fy2017 == 1][[v]]
  tt <- t.test(post, pre)
  data.table(level = lv, variable = v, mean_pre = mean(pre, na.rm = TRUE), mean_post = mean(post, na.rm = TRUE),
             diff = mean(post, na.rm = TRUE) - mean(pre, na.rm = TRUE), p_welch = tt$p.value,
             n_pre = sum(!is.na(pre)), n_post = sum(!is.na(post)))
}))))
fwrite(pp, "results/tables/phase1_prepost.csv")
print(pp, digits = 3)

# 3. OLS: ROE_t on ai_kw_(t-1) + GDP growth (+ crisis dummies), each level, with and without dummies side by side
mods <- list()
for (lv in levels_order) {
  x <- d[level == lv & !is.na(ai_kw_w_lag1)]
  mods[[paste(lv, "no dummies")]] <- lm(roe ~ ai_kw_w_lag1 + gdp_growth, data = x)
  mods[[paste(lv, "with dummies")]] <- lm(roe ~ ai_kw_w_lag1 + gdp_growth + demon + aqr + covid, data = x)
}
cm <- c(ai_kw_w_lag1 = "ai_kw (t-1), per 1 term / 10k words", gdp_growth = "GDP growth (pp)",
        demon = "Demonetisation FY2017", aqr = "AQR FY2016-18", covid = "COVID FY2021", "(Intercept)" = "Constant")
note <- "OLS, conventional SEs; ROE in percent. Descriptive evidence only (n = 14 per level)."
modelsummary(mods, coef_map = cm, gof_map = c("nobs", "r.squared", "adj.r.squared"), stars = TRUE,
             output = "results/tables/phase1_ols.md", notes = note)
tab <- rbindlist(lapply(names(mods), function(m) {
  s <- summary(mods[[m]])$coefficients
  data.table(model = m, term = rownames(s), estimate = s[, 1], se = s[, 2], p = s[, 4], n = nobs(mods[[m]]))
}))
fwrite(tab, "results/tables/phase1_ols.csv")
print(tab[term == "ai_kw_w_lag1"], digits = 3)
