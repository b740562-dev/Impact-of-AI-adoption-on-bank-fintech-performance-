# Phase 2b staggered DiD (docs/spec.md §5): did::att_gt, not-yet-treated controls,
# xformla = ~ baseline_age + baseline_ln_assets; dynamic (event-time) and overall ATT for ROE and stock return.
# Robustness: fixest::sunab (Sun-Abraham); alt1 and alt2 (p50, p75) adoption dates. Run: Rscript src/R/21_did.R
suppressPackageStartupMessages({ library(data.table); library(arrow); library(did); library(fixest); library(ggplot2) })
dir.create("results/tables", FALSE, TRUE); dir.create("results/figures", FALSE, TRUE); dir.create("logs", FALSE)
sink("logs/did.log")
set.seed(20261126)
p <- as.data.table(read_parquet("data/final/panel.parquet"))
p[, id := as.integer(factor(bank_id))]
ctrl <- "ln_assets_l1 + crar_l1 + ldr_l1 + liquidity_ratio_l1 + gnpa_ratio_l1 + pca_l1"
out <- list()
samples <- list("all banks" = p, "excl. YES (post-hoc)" = p[bank_id != "YES"])
for (smp in names(samples)) for (y in c("roe", "stock_ret_pct")) for (g in c("gname_main", "gname_alt1", "gname_alt2_p50", "gname_alt2_p75")) {
  d <- samples[[smp]][!is.na(get(y))]
  a <- tryCatch(att_gt(yname = y, tname = "fy", idname = "id", gname = g, data = as.data.frame(d),
                       xformla = ~ baseline_age + baseline_ln_assets, control_group = "notyettreated",
                       allow_unbalanced_panel = TRUE, est_method = "dr", bstrap = TRUE, cband = TRUE),
                error = function(e) { cat("att_gt failed", y, g, conditionMessage(e), "\n"); NULL })
  if (!is.null(a)) {
    simple <- aggte(a, type = "simple", na.rm = TRUE); dyn <- aggte(a, type = "dynamic", na.rm = TRUE)
    out[[length(out) + 1]] <- data.table(sample = smp, outcome = y, adoption = g, estimator = "CS (did)", term = "overall ATT",
                                         estimate = simple$overall.att, se = simple$overall.se, n_units = length(unique(d$id)))
    out[[length(out) + 1]] <- data.table(sample = smp, outcome = y, adoption = g, estimator = "CS (did)",
                                         term = paste0("e=", dyn$egt), estimate = dyn$att.egt, se = dyn$se.egt,
                                         n_units = length(unique(d$id)))
    if (g == "gname_main") ggsave(sprintf("results/figures/did_event_%s%s.png", y, if (smp == "all banks") "" else "_excl_yes"),
      ggdid(dyn) + labs(title = sprintf("Staggered DiD (Callaway-Sant'Anna): %s, first deployed AI (%s)", y, smp)),
      width = 7, height = 4, dpi = 200)
  }
  d[, g_sa := fifelse(get(g) == 0, 10000L, as.integer(get(g)))]
  sa <- tryCatch(feols(as.formula(sprintf("%s ~ sunab(g_sa, fy) + %s | bank_id + fy", y, ctrl)), d, cluster = ~bank_id),
                 error = function(e) { cat("sunab failed", y, g, conditionMessage(e), "\n"); NULL })
  if (!is.null(sa)) {
    ag <- summary(sa, agg = "ATT")$coeftable
    out[[length(out) + 1]] <- data.table(sample = smp, outcome = y, adoption = g, estimator = "Sun-Abraham (fixest)", term = "ATT",
                                         estimate = ag["ATT", 1], se = ag["ATT", 2], n_units = length(unique(d$id)))
  }
}
tab <- rbindlist(out); tab[, p := 2 * pnorm(-abs(estimate / se))]
fwrite(tab, "results/tables/did_results.csv")
sink()
cat("Units: ROE in percentage points, stock return in percent; effect of post_adopt = 1.\n")
print(tab[term %in% c("overall ATT", "ATT") & adoption %in% c("gname_main", "gname_alt1"), .(sample, outcome, adoption, estimator, estimate = round(estimate, 3),
                                               se = round(se, 3), p = round(p, 3), n_units)])
cat("event-time estimates: results/tables/did_results.csv; plots: results/figures/did_event_*.png\n")
