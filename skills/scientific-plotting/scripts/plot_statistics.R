compare_scientific_groups <- function(data, contrasts, method, experimental_unit, subject = "subject",
                                      confidence = 0.95, adjust = "bh", seed = 2026, bootstrap_samples = 2000) {
  if (!is.character(experimental_unit) || length(experimental_unit) != 1 || !nzchar(trimws(experimental_unit))) stop("Describe the independent experimental_unit")
  if (!method %in% c("paired-t", "welch-t", "wilcoxon") || !is.finite(confidence) || confidence <= 0 || confidence >= 1) stop("Unsupported method/confidence")
  if (!length(contrasts)) stop("Supply explicit contrasts")
  require_scientific_columns(data, c("group", "value"), "value")
  records <- lapply(contrasts, function(contrast) {
    contrast <- unlist(contrast)
    if (length(contrast) != 2 || contrast[1] == contrast[2]) stop("Each contrast needs two different groups")
    a <- data[as.character(data$group) == contrast[1], , drop = FALSE]
    b <- data[as.character(data$group) == contrast[2], , drop = FALSE]
    if (min(nrow(a), nrow(b)) < 2) stop("Each group needs at least two independent observations")
    if (method != "welch-t") {
      require_scientific_columns(data, subject)
      require_scientific_unique(rbind(a, b), c(subject, "group"))
      if (!setequal(a[[subject]], b[[subject]])) stop("Paired groups require exactly matching subject IDs")
      b <- b[match(a[[subject]], b[[subject]]), , drop = FALSE]
      difference <- b$value - a$value
      if (sd(difference) == 0) stop("Paired differences have zero variance")
      effect <- mean(difference); standardized <- effect / sd(difference)
      if (method == "paired-t") {
        test <- t.test(b$value, a$value, paired = TRUE, conf.level = confidence)
        interval <- test$conf.int; p <- test$p.value; ci_method <- "paired-t mean difference"
      } else {
        if (bootstrap_samples < 100 || bootstrap_samples != as.integer(bootstrap_samples)) stop("bootstrap_samples must be integer >= 100")
        test <- wilcox.test(difference, exact = FALSE); p <- test$p.value
        # Preserve the caller's RNG state.
        had_seed <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
        if (had_seed) old_seed <- get(".Random.seed", envir = .GlobalEnv)
        on.exit(if (had_seed) assign(".Random.seed", old_seed, envir = .GlobalEnv) else if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) rm(".Random.seed", envir = .GlobalEnv), add = TRUE)
        set.seed(seed)
        means <- replicate(bootstrap_samples, mean(sample(difference, replace = TRUE)))
        interval <- quantile(means, c((1-confidence)/2, (1+confidence)/2)); ci_method <- "percentile bootstrap mean difference"
      }
    } else {
      if (subject %in% names(data)) {
        require_scientific_columns(data, subject)
        require_scientific_unique(rbind(a, b), c(subject, "group"))
        if (length(intersect(a[[subject]], b[[subject]]))) stop("Overlapping subject IDs require a paired design")
      }
      if (var(a$value) + var(b$value) == 0) stop("Both groups have zero variance")
      test <- t.test(b$value, a$value, var.equal = FALSE, conf.level = confidence)
      effect <- mean(b$value) - mean(a$value); interval <- test$conf.int; p <- test$p.value
      pooled <- sqrt(((nrow(a)-1)*var(a$value)+(nrow(b)-1)*var(b$value))/(nrow(a)+nrow(b)-2))
      standardized <- effect / pooled; ci_method <- "Welch mean difference"
    }
    data.frame(first = contrast[1], second = contrast[2], n_first = nrow(a), n_second = nrow(b),
               effect = effect, ci_low = unname(interval[1]), ci_high = unname(interval[2]), confidence = confidence,
               standardized_effect = standardized, standardized_definition = if (method == "welch-t") "Cohen d" else "Cohen dz",
               p = p, method = method, ci_method = ci_method, experimental_unit = experimental_unit)
  })
  result <- do.call(rbind, records)
  correction <- switch(adjust, bh = "BH", bonferroni = "bonferroni", none = "none", stop("Unsupported adjustment"))
  result$p_adjusted <- p.adjust(result$p, method = correction)
  result$adjustment <- adjust
  result
}

annotate_scientific_comparisons <- function(plot, results, levels, data) {
  span <- max(diff(range(data$value)), 1e-6); step <- span * 0.16
  foreground <- .sp_or(plot$theme$text$colour, "#202020")
  for (i in seq_len(nrow(results))) {
    row <- results[i, ]; x1 <- match(row$first, levels); x2 <- match(row$second, levels)
    y <- max(data$value) + i * step
    plot <- plot + ggplot2::annotate("segment", x = x1, xend = x2, y = y, yend = y, linewidth = 0.3, colour = foreground) +
      ggplot2::annotate("text", x = (x1+x2)/2, y = y+0.2*step, label = sprintf("%s p=%.3g", row$adjustment, row$p_adjusted), size = 2.5, colour = foreground)
  }
  plot
}
