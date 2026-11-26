# Robustness (docs/spec.md §5): winsorised outcomes (1/99), lagged profit growth control, year-standardised ai_kw,
# ai_kw_ln, drop merger years, and other proxies (ai_events_cum; ai_patents / fintech_idx / ai_calls when present).
# Main FE spec: outcome ~ AI(t-1) + controls(t-1) | bank + FY, SEs clustered by bank. Run: Rscript src/R/40_robustness.R
suppressPackageStartupMessages({ library(data.table); library(arrow); library(fixest) })
dir.create("results/tables", FALSE, TRUE)
p <- as.data.table(read_parquet("data/final/panel.parquet"))
std <- function(x) x / sd(x, na.rm = TRUE)
wins <- function(x) { q <- quantile(x, c(.01, .99), na.rm = TRUE); pmin(pmax(x, q[1]), q[2]) }
p[, `:=`(ai_l1 = std(ai_kw_l1), ai_z_l1 = ai_kw_z_l1, ai_ln_l1 = std(ai_kw_ln_l1), ev_l1 = std(ai_events_cum_l1))]
for (v in c("fintech_idx", "ai_patents", "ai_calls")) if (v %in% names(p)) p[, (paste0(v, "_l1")) := std(shift(get(v))), by = bank_id]
ctrl <- "ln_assets_l1 + crar_l1 + ldr_l1 + liquidity_ratio_l1 + gnpa_ratio_l1 + pca_l1"
specs <- list(
  "baseline" = list(ai = "ai_l1", data = p, extra = ""),
  "winsorised outcome 1/99" = list(ai = "ai_l1", data = p, extra = "", wins = TRUE),
  "+ lagged profit growth" = list(ai = "ai_l1", data = p, extra = "+ profit_growth_l1"),
  "year-standardised ai_kw" = list(ai = "ai_z_l1", data = p, extra = ""),
  "ai_kw_ln = ln(1+count)" = list(ai = "ai_ln_l1", data = p, extra = ""),
  "drop merger years" = list(ai = "ai_l1", data = p[merger_year == 0], extra = ""),
  "ai_events_cum" = list(ai = "ev_l1", data = p, extra = ""))
for (v in c("fintech_idx", "ai_patents")) {
  a <- paste0(v, "_l1")
  if (!a %in% names(p)) next
  if (isTRUE(sd(p[[a]], na.rm = TRUE) > 0)) specs[[v]] <- list(ai = a, data = p, extra = "")
  else message(v, ": no variation across banks and years, not estimated (docs/spec_changes.md)")
}
if ("ai_calls_l1" %in% names(p)) specs[["ai_calls (FY2022+)"]] <- list(ai = "ai_calls_l1", data = p[fy >= 2023], extra = "")
out <- list()
for (y in c("roe", "stock_ret_pct", "roa", "tobins_q")) for (s in names(specs)) {
  sp <- specs[[s]]; d <- copy(sp$data); yy <- y
  if (isTRUE(sp$wins)) { d[, yw := wins(get(y))]; yy <- "yw" }
  m <- tryCatch(feols(as.formula(sprintf("%s ~ %s + %s %s | bank_id + fy", yy, sp$ai, ctrl, sp$extra)), d, cluster = ~bank_id),
                error = function(e) NULL)
  if (is.null(m)) next
  ct <- coeftable(m)[sp$ai, ]
  out[[length(out) + 1]] <- data.table(outcome = y, spec = s, proxy = sp$ai, estimate = ct[1], se = ct[2], p = ct[4], n = nobs(m))
}
tab <- rbindlist(out)
fwrite(tab, "results/tables/robustness.csv")
cat("Coefficient = effect of 1 SD of the AI proxy (t-1); ROE/ROA in pp, stock return in %.\n")
print(tab[outcome %in% c("roe", "stock_ret_pct"), .(outcome, spec, estimate = round(estimate, 3), se = round(se, 3), p = round(p, 3), n)])
cat("full table: results/tables/robustness.csv\n")
