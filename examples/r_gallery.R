# Synthetic shared data, seed 2026. Run: Rscript examples/r_gallery.R [out] [preset]
args <- commandArgs(trailingOnly = TRUE)
script <- sub("^--file=", "", commandArgs()[grepl("^--file=", commandArgs())][1])
root <- dirname(dirname(normalizePath(script)))
out <- if (length(args)) args[[1]] else file.path(root, "build", "r")
selected <- if (length(args) >= 2) args[[2]] else "all"
library(ggplot2)
library(patchwork)
source(file.path(root, "skills", "scientific-plotting", "scripts", "scientific_style.R"))
groups <- c("Model A", "Model B", "Model C")
read_data <- function(name) {
  data <- read.csv(file.path(root, "examples", "data", paste0(name, ".csv")))
  if ("group" %in% names(data)) data$group <- factor(data$group, levels = groups)
  data
}
curves <- read_data("curves")
distributions <- read_data("distributions")
scatter <- read_data("scatter")
matrix <- read_data("matrix")
matrix$feature <- factor(matrix$feature, levels = rev(unique(matrix$feature)))
presets <- if (selected == "all") names(.sp_config$presets) else selected
for (preset in presets) {
  config <- scientific_preset(preset)
  theme <- scientific_theme(preset) + theme(legend.position = "none")
  p1 <- ggplot(curves, aes(x, response, colour = group, linetype = group, shape = group)) +
    geom_line(linewidth = 0.5) + geom_point(size = 1.1) + scientific_scales(groups, preset) + theme +
    labs(title = "A  Response curves", x = "Time (h)", y = "Response (a.u.)") +
    theme(legend.position = "inside", legend.position.inside = c(0.73, 0.25), legend.title = element_blank(), legend.text = element_text(size = config$font_size * 0.8))
  p2 <- ggplot(distributions, aes(group, value, colour = group, fill = group)) +
    geom_boxplot(width = 0.5, alpha = 0.2, outlier.shape = NA, linewidth = 0.35) +
    geom_point(aes(shape = group), position = position_jitter(width = 0.13, height = 0, seed = 2026), size = 1.2, alpha = 0.75) +
    scientific_scales(groups, preset) + theme + labs(title = "B  Distributions", x = NULL, y = "Score (a.u.)")
  p3 <- ggplot(scatter, aes(x, y, colour = group, shape = group)) + geom_point(size = 1.3, alpha = 0.8) +
    scientific_scales(groups, preset) + theme + labs(title = "C  Association", x = "Input (a.u.)", y = "Output (a.u.)")
  limit <- max(abs(matrix$value))
  heat_scale <- if (preset == "ieee") scale_fill_gradient(low = "white", high = "#202020", limits = c(-limit, limit)) else
    scale_fill_gradient2(low = "#2166AC", mid = "white", high = "#B2182B", midpoint = 0, limits = c(-limit, limit))
  p4 <- ggplot(matrix, aes(sample, feature, fill = value)) + geom_tile() + heat_scale +
    scale_x_discrete(labels = paste0("S", 1:5)) + scale_y_discrete(labels = paste0("F", 4:1)) +
    theme + theme(panel.grid = element_blank(), legend.position = "right") +
    guides(fill = guide_colourbar(barheight = grid::unit(28 * config$font_size / 9, "mm"),
                                  barwidth = grid::unit(3 * config$font_size / 9, "mm"))) +
    labs(title = "D  Signed matrix", x = NULL, y = NULL, fill = "Value\n(a.u.)")
  plot <- wrap_plots(p1, p2, p3, p4, ncol = 2) +
    plot_annotation(title = paste(toupper(preset), "· R | SYNTHETIC DATA"),
                    theme = scientific_theme(preset) + theme(plot.title = element_text(size = config$font_size + 1)))
  size <- switch(preset, presentation = c(260, 200), poster = c(350, 270), c(180, 140))
  export_scientific(plot, file.path(out, paste0("r-", preset)), width_mm = size[1], height_mm = size[2], dpi = 180,
                    metadata = list(preset = preset, synthetic = TRUE, seed = 2026, source = "examples/data/*.csv"))
}
