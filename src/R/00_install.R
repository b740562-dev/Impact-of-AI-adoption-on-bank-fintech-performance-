# Install R packages used by the estimation scripts (run once).
pkgs <- c("fixest", "did", "data.table", "arrow", "ggplot2", "modelsummary", "fwildclusterboot", "sandwich", "lmtest")
missing <- setdiff(pkgs, rownames(installed.packages()))
if (length(missing)) install.packages(missing, repos = "https://cloud.r-project.org")
invisible(lapply(pkgs, function(p) cat(sprintf("%-18s %s\n", p, as.character(packageVersion(p))))))
