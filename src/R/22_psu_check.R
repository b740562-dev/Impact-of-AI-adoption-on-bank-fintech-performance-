# POST-HOC check of the AI x PSU interaction (docs/spec_changes.md 2026-11-26).
# Question: is the positive AI x PSU effect a PSU-specific time trend (post-AQR recovery) rather than AI?
# Specs (lag 1, AI = 1 SD of ai_kw, controls lagged, SEs clustered by bank):
#   (1) original:              Y ~ AI + AI:PSU + X | bank + FY
#   (2) PSU-specific year FE:  Y ~ AI + AI:PSU + X | bank + PSU^FY
#   (3) bank-specific trends:  Y ~ AI + AI:PSU + X | bank[FY] + FY      (each bank its own linear trend)
# Reports the interaction, the implied PSU slope (AI + AI:PSU) with clustered SE, and wild-bootstrap p for (1)-(2).
# Run: Rscript src/R/22_psu_check.R
suppressPackageStartupMessages({ library(data.table); library(arrow); library(fixest) })
set.seed(20261126)
p <- as.data.table(read_parquet("data/final/panel.parquet"))
sd_kw <- sd(p$ai_kw, na.rm = TRUE)
p[, ai_l1 := ai_kw_l1 / sd_kw]
p[, psu_fy := paste(psu, fy)]
ctrl <- "ln_assets_l1 + crar_l1 + ldr_l1 + liquidity_ratio_l1 + gnpa_ratio_l1 + pca_l1"

# wild cluster restricted bootstrap-t (Webb weights), same implementation as 20_fe.R, FE set passed in
cr1_t <- function(X, y, cl, k) {
  XtXi <- solve(crossprod(X)); b <- XtXi %*% crossprod(X, y); u <- as.vector(y - X %*% b)
  S <- rowsum(X * u, cl); G <- nrow(S); N <- nrow(X); K <- ncol(X)
  V <- XtXi %*% crossprod(S) %*% XtXi * (G / (G - 1)) * ((N - 1) / (N - K))
  b[k] / sqrt(V[k, k])
}
boot_p <- function(m, param, fes, B = 9999) {
  tryCatch({
    idx <- obs(m)
    X0 <- model.matrix(m, type = "rhs"); y0 <- model.matrix(m, type = "lhs")
    dm <- demean(cbind(y = as.vector(y0), X0), f = as.data.frame(p[idx, ..fes]))
    y <- dm[, 1]; X <- dm[, -1, drop = FALSE]; cl <- p$bank_id[idx]; k <- match(param, colnames(X))
    t0 <- cr1_t(X, y, cl, k)
    Xr <- X[, -k, drop = FALSE]; fit_r <- as.vector(Xr %*% solve(crossprod(Xr), crossprod(Xr, y))); u_r <- y - fit_r
    g <- as.integer(factor(cl)); G <- max(g)
    w6 <- c(-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5))
    tb <- vapply(seq_len(B), function(i) cr1_t(X, fit_r + u_r * sample(w6, G, TRUE)[g], cl, k), numeric(1))
    mean(abs(tb) >= abs(t0))
  }, error = function(e) { message("bootstrap failed: ", conditionMessage(e)); NA_real_ })
}

specs <- list(
  "(1) original: bank + FY FE"       = list(fe = "bank_id + fy",     boot = c("bank_id", "fy")),
  "(2) PSU-specific year FE"         = list(fe = "bank_id + psu_fy", boot = c("bank_id", "psu_fy")),
  "(3) bank-specific linear trends"  = list(fe = "bank_id[fy] + fy", boot = NULL))
res <- list()
for (y in c("roe", "stock_ret_pct", "roa", "tobins_q")) for (s in names(specs)) {
  m <- feols(as.formula(sprintf("%s ~ ai_l1 + ai_l1:psu + %s | %s", y, ctrl, specs[[s]]$fe)), p, cluster = ~bank_id)
  b <- coef(m); V <- vcov(m); G <- length(unique(p[obs(m), bank_id]))
  int <- "ai_l1:psu"
  psu_b <- b["ai_l1"] + b[int]
  psu_se <- sqrt(V["ai_l1", "ai_l1"] + V[int, int] + 2 * V["ai_l1", int])
  ct <- coeftable(m)
  res[[length(res) + 1]] <- data.table(
    outcome = y, spec = s, interaction = ct[int, 1], se_int = ct[int, 2], p_int = ct[int, 4],
    p_int_wild = if (is.null(specs[[s]]$boot)) NA_real_ else boot_p(m, int, specs[[s]]$boot),
    private_slope = ct["ai_l1", 1], p_private = ct["ai_l1", 4],
    psu_slope = psu_b, se_psu = psu_se, p_psu = 2 * pt(abs(psu_b / psu_se), df = G - 1, lower.tail = FALSE),
    n = nobs(m), n_banks = G)
}
tab <- rbindlist(res)
dir.create("results/tables", FALSE, TRUE)
fwrite(tab, "results/tables/fe_psu_check.csv")
cat("POST-HOC. AI = 1 SD of ai_kw at t-1; ROE/ROA in pp, stock return in %. PSU slope = AI + AI:PSU.\n")
print(tab[, .(outcome, spec, interaction = round(interaction, 2), p_int = round(p_int, 3), p_wild = round(p_int_wild, 3),
              private = round(private_slope, 2), psu_slope = round(psu_slope, 2), p_psu = round(p_psu, 3), n)])
cat("full table: results/tables/fe_psu_check.csv\n")
