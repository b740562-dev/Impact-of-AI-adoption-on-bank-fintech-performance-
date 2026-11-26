# POST-HOC DiD diagnostics (docs/spec_changes.md 2026-11-26, §5 Phase 2b post-hoc entry).
# Concern: late/never-treated banks are mostly PSU banks whose ROE fell to about -10.7 (FY2018, AQR) and recovered to
# about +12.9 (FY2025), so they are poor controls for early (private) adopters.
# Main adoption definition only (gname_main = FY of first deployed AI system); outcomes ROE (pp) and stock return (%).
#   (a) Callaway-Sant'Anna on PRIVATE banks only: controls = not-yet-treated + never-treated private banks;
#       xformla = ~ baseline_age + baseline_ln_assets as in 21_did.R (falls back to ~1 if it fails; logged in column).
#   (b) Sun-Abraham on all banks with bank FE + PSU x FY FE (controls lagged as in 21_did.R), SE clustered by bank.
# Cohorts adopting after the outcome's last observed FY are coded never-treated in that outcome's sample (as did does).
# Output: results/tables/did_posthoc.csv (overall ATT, event-time incl. pre-trend coefficients, n treated / control,
# joint pre-trend Wald p), results/figures/did_posthoc_cs_private_*.png. Run: Rscript src/R/23_did_posthoc.R
suppressPackageStartupMessages({ library(data.table); library(arrow); library(did); library(fixest); library(ggplot2) })
dir.create("results/tables", FALSE, TRUE); dir.create("results/figures", FALSE, TRUE); dir.create("logs", FALSE)
sink("logs/did_posthoc.log")
set.seed(20261126)
p <- as.data.table(read_parquet("data/final/panel.parquet"))
p[, id := as.integer(factor(bank_id))]
ctrl <- "ln_assets_l1 + crar_l1 + ldr_l1 + liquidity_ratio_l1 + gnpa_ratio_l1 + pca_l1"
out <- list()
add <- function(...) out[[length(out) + 1]] <<- data.table(...)

for (y in c("roe", "stock_ret_pct")) {
  ## (a) CS, private banks only
  d <- p[psu == 0 & !is.na(get(y))]
  maxfy <- max(d$fy); minfy <- min(d$fy)
  d[, g := fifelse(gname_main > maxfy, 0L, as.integer(gname_main))]
  n_tr <- uniqueN(d[g > minfy, id]); n_co <- uniqueN(d[g == 0, id])
  xf <- "~ baseline_age + baseline_ln_assets"
  fit <- function(f) att_gt(yname = y, tname = "fy", idname = "id", gname = "g", data = as.data.frame(d),
                            xformla = as.formula(f), control_group = "notyettreated", allow_unbalanced_panel = TRUE,
                            est_method = "dr", bstrap = TRUE, cband = TRUE)
  a <- tryCatch(fit(xf), error = function(e) { cat("CS with covariates failed:", y, conditionMessage(e), "\n"); NULL })
  if (is.null(a)) { xf <- "~ 1"; a <- tryCatch(fit(xf), error = function(e) { cat("CS ~1 failed:", y, conditionMessage(e), "\n"); NULL }) }
  if (!is.null(a)) {
    s <- aggte(a, type = "simple", na.rm = TRUE); dyn <- aggte(a, type = "dynamic", na.rm = TRUE)
    lab <- list(spec = "(a) CS, private banks only", outcome = y, xformla = xf, n_treated = n_tr, n_control_never = n_co,
                pretrend_wald_p = if (is.null(a$Wpval)) NA_real_ else as.numeric(a$Wpval))
    do.call(add, c(lab, list(term = "overall ATT", estimate = s$overall.att, se = s$overall.se)))
    do.call(add, c(lab, list(term = paste0("e=", dyn$egt), estimate = dyn$att.egt, se = dyn$se.egt)))
    print(summary(a))
    ggsave(sprintf("results/figures/did_posthoc_cs_private_%s.png", y),
      ggdid(dyn) + labs(title = sprintf("POST-HOC: CS DiD, private banks only: %s, first deployed AI", y)),
      width = 7, height = 4, dpi = 200)
  }

  ## (b) Sun-Abraham, all banks, bank FE + PSU x FY FE
  d <- p[!is.na(get(y))]
  maxfy <- max(d$fy)
  d[, g_sa := fifelse(gname_main == 0 | gname_main > maxfy, 10000L, as.integer(gname_main))]
  sa <- tryCatch(feols(as.formula(sprintf("%s ~ sunab(g_sa, fy) + %s | bank_id + psu^fy", y, ctrl)), d, cluster = ~bank_id),
                 error = function(e) { cat("sunab failed:", y, conditionMessage(e), "\n"); NULL })
  if (!is.null(sa)) {
    est <- obs(sa); de <- d[est]
    ct <- coeftable(sa); ev <- ct[grepl("^fy::", rownames(ct)), , drop = FALSE]
    # joint test of the cohort-level lead coefficients is not computable: more restrictions than the 25 clusters,
    # so the clustered VCOV is rank-deficient (wald() returns NA). Reported as NA; individual leads are in the table.
    wp <- tryCatch(wald(sa, keep = "^fy::-", print = FALSE)$p, error = function(e) NA_real_)
    lab <- list(spec = "(b) Sun-Abraham, bank FE + PSU x FY FE", outcome = y, xformla = "controls(t-1)",
                n_treated = uniqueN(de[g_sa < 10000, bank_id]), n_control_never = uniqueN(de[g_sa == 10000, bank_id]),
                pretrend_wald_p = wp)
    ag <- summary(sa, agg = "ATT")$coeftable
    do.call(add, c(lab, list(term = "overall ATT", estimate = ag["ATT", 1], se = ag["ATT", 2])))
    do.call(add, c(lab, list(term = sub("^fy::", "e=", rownames(ev)), estimate = ev[, 1], se = ev[, 2])))
    print(summary(sa))
  }
}
tab <- rbindlist(out, fill = TRUE); tab[, p := 2 * pnorm(-abs(estimate / se))]
tab[, e := suppressWarnings(as.integer(sub("e=", "", term)))]
fwrite(tab[, !"e"], "results/tables/did_posthoc.csv")
sink()

cat("POST-HOC DiD, main adoption. ROE in pp, stock return in %; effect of post_adopt = 1.\n")
for (r in split(tab, by = c("spec", "outcome"))) {
  o <- r[term == "overall ATT"]; pre <- r[!is.na(e) & e < 0]
  cat(sprintf("%s | %s: ATT %.2f (SE %.2f, p=%.3f); n treated %d, never/late %d; leads %d (range %.1f to %.1f, %d with p<0.05), joint pre p=%s\n",
              o$spec, o$outcome, o$estimate, o$se, o$p, o$n_treated, o$n_control_never, nrow(pre),
              min(pre$estimate), max(pre$estimate), sum(pre$p < 0.05), if (is.na(o$pretrend_wald_p)) "n/a" else formatC(o$pretrend_wald_p, digits = 3, format = "f")))
}
cat("details: results/tables/did_posthoc.csv; logs/did_posthoc.log\n")
