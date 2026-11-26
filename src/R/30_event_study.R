# Phase 3 event study (docs/spec.md §5): market model [-250,-30] (min 120 valid days), CAR[-1,+1] and CAR[-5,+5],
# Kolari-Pynnonen adjusted BMP test and Corrado rank test. Benchmark Nifty 500 (main), Nifty Bank (robustness).
# Exclusions: earnings within +/-3 trading days, crisis windows (data/raw/crisis_windows.csv); the firm's other event
# days are dropped from its estimation window. Run from project root: Rscript src/R/30_event_study.R
suppressPackageStartupMessages({ library(data.table); library(arrow); library(ggplot2) })
dir.create("results/tables", FALSE, TRUE); dir.create("results/figures", FALSE, TRUE); dir.create("logs", FALSE)
sink("logs/event_study.log", split = FALSE)

px <- as.data.table(read_parquet("data/interim/prices_daily.parquet"))[, .(id, date = as.IDate(date), ret)]
ev <- fread("data/final/events_clean.csv")[verified == "Y" & car_eligible == "Y"]
ev[, event_trade_date := as.IDate(event_trade_date)]
cw <- fread("data/raw/crisis_windows.csv")[, `:=`(start = as.IDate(start), end = as.IDate(end))]
ev[, in_crisis := mapply(function(f, d) any(cw$firm_id == f & d >= cw$start & d <= cw$end), firm_id, event_trade_date)]
ev[, excluded := fifelse(in_crisis, "crisis window", fifelse(earnings_within_3d %in% "Y", "earnings +/-3d", ""))]
cat("events CAR-eligible:", nrow(ev), " excluded:", sum(ev$excluded != ""), "\n"); print(ev[excluded != "", .(event_id, firm_id, event_trade_date, excluded)])

run <- function(bench, evs) {
  m <- px[id == bench, .(date, rm = ret)]
  cal <- sort(m$date)
  out <- list(); res <- list(); pan <- list()
  for (i in seq_len(nrow(evs))) {
    e <- evs[i]; k <- match(e$event_trade_date, cal); if (is.na(k) || k <= 250) next
    other <- setdiff(evs[firm_id == e$firm_id, event_trade_date], e$event_trade_date)
    f <- merge(px[id == e$firm_id, .(date, ri = ret)], m, by = "date")
    f[, tau := match(date, cal) - k]
    est <- f[tau >= -250 & tau <= -30 & !(date %in% other) & is.finite(ri) & is.finite(rm)]
    if (nrow(est) < 120) next
    fit <- lm(ri ~ rm, est); s <- sigma(fit); T_ <- nrow(est)
    w <- f[tau >= -5 & tau <= 5][, ar := ri - predict(fit, .SD)]
    rmbar <- mean(est$rm); sxx <- sum((est$rm - rmbar)^2)
    car_sd <- function(a, b) { x <- w[tau >= a & tau <= b]; L <- nrow(x)
      s * sqrt(L + L^2 / T_ + (sum(x$rm) - L * rmbar)^2 / sxx) }
    out[[length(out) + 1]] <- data.table(event_id = e$event_id, firm_id = e$firm_id, bank_type = e$bank_type,
      category = e$category, car_m1p1 = w[tau >= -1 & tau <= 1, sum(ar)], car_m5p5 = sum(w$ar),
      scar_m1p1 = w[tau >= -1 & tau <= 1, sum(ar)] / car_sd(-1, 1), scar_m5p5 = sum(w$ar) / car_sd(-5, 5), n_est = T_)
    res[[e$event_id]] <- data.table(date = est$date, u = residuals(fit))
    allw <- rbind(est[, .(tau, ar = residuals(fit))], w[, .(tau, ar)])
    allw[, U := frank(ar) / (.N + 1) - 0.5]; pan[[e$event_id]] <- allw[, .(event_id = e$event_id, tau, U, ar)]
  }
  car <- rbindlist(out)
  # Kolari-Pynnonen: average pairwise correlation of estimation residuals (overlapping dates)
  ids <- names(res); rs <- c()
  if (length(ids) > 1) for (a in 1:(length(ids) - 1)) for (b in (a + 1):length(ids)) {
    z <- merge(res[[ids[a]]], res[[ids[b]]], by = "date"); if (nrow(z) >= 30) rs <- c(rs, cor(z$u.x, z$u.y)) }
  rbar <- if (length(rs)) mean(rs) else 0
  list(car = car, rbar = rbar, ranks = rbindlist(pan))
}

tests <- function(r, sub, label) {
  car <- r$car[event_id %in% sub]; N <- nrow(car); if (N < 2) return(NULL)
  rk <- r$ranks[event_id %in% sub]; ubar <- rk[, .(ub = mean(U)), by = tau]; S <- sqrt(mean(ubar$ub^2))
  rbindlist(lapply(list(c(-1, 1, "car_m1p1", "scar_m1p1"), c(-5, 5, "car_m5p5", "scar_m5p5")), function(x) {
    a <- as.numeric(x[1]); b <- as.numeric(x[2]); sc <- car[[x[4]]]
    t_bmp <- mean(sc) * sqrt(N) / sd(sc); t_kp <- t_bmp * sqrt((1 - r$rbar) / (1 + (N - 1) * r$rbar))
    L <- b - a + 1; t_rank <- ubar[tau >= a & tau <= b, sum(ub)] / (sqrt(L) * S)
    data.table(group = label, window = sprintf("[%d,%+d]", a, b), N = N, mean_car_pct = 100 * mean(car[[x[3]]]),
               median_car_pct = 100 * median(car[[x[3]]]), t_bmp = t_bmp, t_kp = t_kp,
               p_kp = 2 * pt(-abs(t_kp), N - 1), t_corrado = t_rank, p_corrado = 2 * pnorm(-abs(t_rank)), rbar = r$rbar)
  }))
}

main_ev <- ev[excluded == ""]
# POST-HOC overlap rule (docs/spec_changes.md 2026-11-26): same-firm events whose [-5,+5] windows overlap
# (<= 10 trading days apart) -> keep only the earlier one.
cal0 <- sort(unique(px[id == "NIFTY500", date]))
setorder(main_ev, firm_id, event_trade_date); main_ev[, k := findInterval(event_trade_date, cal0)]
main_ev[, keep := { kk <- k; ok <- rep(TRUE, .N); last <- -Inf
  for (j in seq_len(.N)) { if (kk[j] - last <= 10) ok[j] <- FALSE else last <- kk[j] }; ok }, by = firm_id]
cat("overlap rule dropped:", paste(main_ev[keep == FALSE, event_id], collapse = ", "), "\n")
overlap_dropped <- main_ev[keep == FALSE, event_id]
main_ev <- main_ev[keep == TRUE][, c("k", "keep") := NULL]
all_out <- list()
for (bench in c("NIFTY500", "NIFTYBANK")) {
  r <- run(bench, main_ev)
  fwrite(r$car, sprintf("results/tables/event_car_%s.csv", tolower(bench)))
  grp <- list(All = r$car$event_id)
  for (bt in unique(r$car$bank_type)) grp[[paste("type:", bt)]] <- r$car[bank_type == bt, event_id]
  for (ct in unique(r$car$category)) grp[[paste("category:", ct)]] <- r$car[category == ct, event_id]
  tb <- rbindlist(lapply(names(grp), function(g) tests(r, grp[[g]], g)))
  tb[, benchmark := bench]; all_out[[bench]] <- tb
  if (bench == "NIFTY500") {
    avg <- r$ranks[, .(car = mean(ar)), by = tau][tau >= -5][order(tau)][, cum := 100 * cumsum(car)]
    p <- ggplot(avg, aes(tau, cum)) + geom_hline(yintercept = 0, colour = "grey60") + geom_line() + geom_point() +
      labs(title = "Average CAR around AI announcements (market model, Nifty 500)", x = "Trading day relative to event",
           y = "Cumulative abnormal return (%)", caption = sprintf("N = %d events", nrow(r$car))) + theme_minimal()
    ggsave("results/figures/event_car_path.png", p, width = 7, height = 4, dpi = 200)
  }
}
tab <- rbindlist(all_out)
fwrite(tab, "results/tables/event_study_tests.csv")
sink()
print(tab[group == "All" | grepl("type:", group), .(benchmark, group, window, N, mean_car_pct = round(mean_car_pct, 2),
                                                    p_kp = round(p_kp, 3), p_corrado = round(p_corrado, 3))])
cat("overlap rule (post-hoc) dropped:", paste(overlap_dropped, collapse = ", "), "\n")
cat("details: logs/event_study.log; tables: results/tables/event_study_tests.csv\n")
