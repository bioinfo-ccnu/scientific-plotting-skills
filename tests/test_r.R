script <- sub("^--file=", "", commandArgs()[grepl("^--file=", commandArgs())][1])
root <- dirname(dirname(normalizePath(script)))
source(file.path(root, "skills/scientific-plotting/scripts/scientific_style.R"))
library(ggplot2)
out <- tempfile("scientific-plotting-test-")
dir.create(out)
fails <- function(expr) inherits(tryCatch({force(expr); NULL}, error = identity), "error")
data <- data.frame(x = rep(1:3, 2), y = c(1, 2, 1, 2, 3, 2), group = rep(c("Control", "Treatment"), each = 3))
for (preset in names(.sp_config$presets)) {
  p <- ggplot(data, aes(x, y, colour = group, shape = group, linetype = group)) +
    geom_line() + geom_point() + scientific_theme(preset) + scientific_scales(c("Control", "Treatment"), preset)
  paths <- export_scientific(p, file.path(out, preset), formats = c("pdf", "svg", "png", "tiff"),
                            width_mm = 100, height_mm = 70, dpi = 100,
                            metadata = list(synthetic = TRUE, preset = preset))
  stopifnot(all(file.exists(paths)), all(file.info(paths)$size > 100))
  record <- jsonlite::fromJSON(paths[["manifest"]])
  stopifnot(record$width_mm == 100, record$height_mm == 70, record$metadata$synthetic)
  stopifnot(abs(record$pdf_page_mm$width - 100) < 25.4 / 72,
            abs(record$pdf_page_mm$height - 70) < 25.4 / 72)
  svg <- paste(readLines(paths[["svg"]], warn = FALSE), collapse = "\n")
  svg_header <- grep("^<svg", readLines(paths[["svg"]], warn = FALSE), value = TRUE)
  width_pt <- as.numeric(sub(".*width=['\"]([0-9.]+)pt['\"].*", "\\1", svg_header))
  height_pt <- as.numeric(sub(".*height=['\"]([0-9.]+)pt['\"].*", "\\1", svg_header))
  stopifnot(grepl("<text", svg, fixed = TRUE), abs(width_pt - 100 / 25.4 * 72) < 0.01,
            abs(height_pt - 70 / 25.4 * 72) < 0.01)
  png_header <- readBin(paths[["png"]], "raw", n = 24)
  unsigned32 <- function(bytes) sum(as.integer(bytes) * 256^(3:0))
  stopifnot(abs(unsigned32(png_header[17:20]) - 100 / 25.4 * 100) <= 1,
            abs(unsigned32(png_header[21:24]) - 70 / 25.4 * 100) <= 1)
}
existing <- file.path(out, "existing.png")
writeLines("keep me", existing)
stopifnot(fails(export_scientific(p, file.path(out, "existing"))))
stopifnot(identical(readLines(existing), "keep me"), !file.exists(file.path(out, "existing.pdf")))
stopifnot(fails(export_scientific(p, file.path(out, "invalid"), dpi = 0)))
stopifnot(fails(export_scientific(p, file.path(out, "invalid"), formats = c("png", "jpeg"))))
stopifnot(fails(scientific_palette(9)), fails(scientific_colors(c("A", "A"))))
stopifnot(identical(unname(scientific_colors(c("Control", "Treatment"))), c("#0072B2", "#D55E00")))
unlink(out, recursive = TRUE)
cat("R checks passed: 8 presets, 4 formats, physical SVG dimensions, metadata, collision handling and category mappings\n")
