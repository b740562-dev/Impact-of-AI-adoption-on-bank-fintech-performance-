# Install R packages used by the estimation scripts (run once). Uses the per-user library (no admin rights needed).
options(timeout = 1800)  # default 60 s fails for large binaries (stringi, BH, arrow)
lib <- Sys.getenv("R_LIBS_USER")
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
pkgs <- c("fixest", "did", "data.table", "arrow", "ggplot2", "modelsummary", "fwildclusterboot", "sandwich", "lmtest")
missing <- setdiff(pkgs, rownames(installed.packages()))
if (length(missing)) install.packages(missing, lib = lib, repos = "https://cloud.r-project.org")
invisible(lapply(pkgs, function(p) cat(sprintf("%-18s %s\n", p,
  tryCatch(as.character(packageVersion(p)), error = function(e) "NOT INSTALLED")))))
