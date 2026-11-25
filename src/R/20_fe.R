# Phase 2a two-way FE (docs/spec.md §5): Y_it = b*AI_i,t-1 + g'X_i,t-1 + a_i + d_t + e_it.
# fixest::feols, SEs clustered by bank; wild cluster bootstrap p-values (Webb weights, 9,999 draws).
# AI = ai_kw standardised over the panel (coefficient = effect of 1 SD of ai_kw). Lags 0, 1 (main), 2.
# Outcomes: ROE, stock return (primary); ROA, Tobin's Q (secondary). Run: Rscript src/R/20_fe.R
suppressPackageStartupMessages({ library(data.table); library(arrow); library(fixest); library(fwildclusterboot) })
dir.create("results/tables", FALSE, TRUE); dir.create("logs", FALSE)
sink("logs/fe.log")
set.seed(20261126)
p <- as.data.table(read_parquet("data/final/panel.parquet"))
sd_kw <- sd(p$ai_kw, na.rm = TRUE)
p[, `:=`(ai_l0 = ai_kw / sd_kw, ai_l1 = ai_kw_l1 / sd_kw, ai_l2 = ai_kw_l2 / sd_kw,
         age_std = (baseline_age - mean(baseline_age)) / sd(baseline_age),
         size_std = (ln_assets_l1 - mean(ln_assets_l1, na.rm = TRUE)) / sd(ln_assets_l1, na.rm = TRUE))]
ctrl <- "ln_assets_l1 + crar_l1 + ldr_l1 + liquidity_ratio_l1 + gnpa_ratio_l1 + pca_l1"
outcomes <- c(roe = "ROE (%)", stock_ret_pct = "Stock return (%)", roa = "ROA (%)", tobins_q = "Tobin's Q")

boot_p <- function(m, param) {
  b <- tryCatch(boottest(m, param = param, clustid = "bank_id", B = 9999, type = "webb"), error = function(e) NULL)
  if (is.null(b)) NA_real_ else pval(b)
}
row <- function(m, param, y, spec) {
  ct <- coeftable(m)
  data.table(outcome = y, spec = spec, term = param, estimate = ct[param, 1], se = ct[param, 2], p_cluster = ct[param, 4],
             p_wild = boot_p(m, param), n = nobs(m), n_banks = length(unique(p[obs(m), bank_id])))
}
res <- list(); mods <- list()
for (y in names(outcomes)) {
  for (lag in c("ai_l0", "ai_l1", "ai_l2")) {
    f <- as.formula(sprintf("%s ~ %s + %s | bank_id + fy", y, lag, ctrl))
    m <- feols(f, p, cluster = ~bank_id); mods[[paste(y, lag)]] <- m
    res[[length(res) + 1]] <- row(m, lag, y, paste("main, lag", substr(lag, 5, 5)))
  }
  for (mod in c("psu", "covid", "demon", "post_chatgpt", "age_std", "size_std", "zscore_std")) {
    f <- as.formula(sprintf("%s ~ ai_l1 + ai_l1:%s + %s | bank_id + fy", y, mod, ctrl))
    m <- tryCatch(feols(f, p, cluster = ~bank_id), error = function(e) NULL); if (is.null(m)) next
    term <- grep(paste0("ai_l1:", mod), names(coef(m)), value = TRUE)[1]; if (is.na(term)) next
    res[[length(res) + 1]] <- row(m, term, y, paste("interaction:", mod))
    res[[length(res) + 1]] <- row(m, "ai_l1", y, paste("interaction:", mod, "(main effect)"))
  }
}
tab <- rbindlist(res)
fwrite(tab, "results/tables/fe_results.csv")
etable(mods[grep("ai_l1", names(mods))], file = "results/tables/fe_main.tex", replace = TRUE)
sink()
cat("AI = 1 SD of ai_kw (SD =", round(sd_kw, 3), "terms per 10,000 English words). Lag 1 = pre-specified main.\n")
print(tab[spec %in% c("main, lag 1", "interaction: psu"), .(outcome, spec, term, estimate = round(estimate, 3),
                                                           se = round(se, 3), p_cluster = round(p_cluster, 3), p_wild = round(p_wild, 3), n)])
cat("all specs: results/tables/fe_results.csv\n")
