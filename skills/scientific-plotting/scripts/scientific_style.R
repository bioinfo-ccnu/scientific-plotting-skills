# Original ggplot2 themes analogous to Python presets; no SciencePlots code.
.sp_source <- sys.frame(1)$ofile
if (is.null(.sp_source)) stop("Load scientific_style.R with source()")
.sp_root <- dirname(dirname(normalizePath(.sp_source, mustWork = TRUE)))
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Install jsonlite")
if (!requireNamespace("ggplot2", quietly = TRUE)) stop("Install ggplot2")
.sp_config <- jsonlite::fromJSON(file.path(.sp_root, "assets", "style-presets.json"), simplifyVector = FALSE)

scientific_preset <- function(preset = "science") {
  if (!preset %in% names(.sp_config$presets)) stop("Unknown preset: ", preset)
  .sp_config$presets[[preset]]
}

scientific_palette <- function(n, preset = "science", palette_name = NULL) {
  config <- scientific_preset(preset)
  name <- if (is.null(palette_name)) config$palette else palette_name
  colors <- unlist(.sp_config$palettes[[name]], use.names = FALSE)
  if (!length(colors)) stop("Unknown palette: ", name)
  if (!is.numeric(n) || length(n) != 1L || !is.finite(n) || n != as.integer(n) || n < 1 || n > length(colors)) {
    stop(name, " supports 1–", length(colors), " categories; use another encoding for more")
  }
  colors[seq_len(n)]
}

scientific_colors <- function(levels, preset = "science", palette_name = NULL) {
  if (!is.character(levels) || anyNA(levels) || anyDuplicated(levels)) stop("Category levels must be unique strings")
  stats::setNames(scientific_palette(length(levels), preset, palette_name), levels)
}

scientific_theme <- function(preset = "science", family = NULL) {
  config <- scientific_preset(preset)
  if (is.null(family)) family <- config$family
  base <- if (config$grid) ggplot2::theme_minimal else ggplot2::theme_classic
  background <- config$background
  foreground <- config$foreground
  base(base_size = config$font_size, base_family = family) + ggplot2::theme(
    text = ggplot2::element_text(colour = foreground),
    axis.text = ggplot2::element_text(colour = foreground),
    axis.title = ggplot2::element_text(colour = foreground),
    axis.line = if (config$grid) ggplot2::element_blank() else ggplot2::element_line(colour = foreground, linewidth = 0.3),
    axis.ticks = ggplot2::element_line(colour = foreground),
    plot.background = ggplot2::element_rect(fill = background, colour = NA),
    panel.background = ggplot2::element_rect(fill = background, colour = NA),
    legend.background = ggplot2::element_rect(fill = background, colour = NA),
    legend.key = ggplot2::element_rect(fill = background, colour = NA),
    panel.grid.minor = ggplot2::element_blank(),
    panel.grid.major = if (config$grid) ggplot2::element_line(colour = grDevices::adjustcolor(foreground, alpha.f = 0.15), linewidth = 0.25) else ggplot2::element_blank(),
    plot.title = ggplot2::element_text(face = "bold"),
    strip.background = ggplot2::element_rect(fill = background, colour = NA),
    strip.text = ggplot2::element_text(colour = foreground),
    legend.key.size = grid::unit(3.5, "mm")
  )
}

scientific_scales <- function(levels, preset = "science") {
  colors <- scientific_colors(levels, preset)
  result <- list(
    ggplot2::scale_colour_manual(values = colors, limits = levels, drop = FALSE),
    ggplot2::scale_fill_manual(values = colors, limits = levels, drop = FALSE)
  )
  if (preset %in% c("ieee", "accessible")) {
    result <- c(result, list(
      ggplot2::scale_linetype_manual(values = stats::setNames(rep(c("solid", "dashed", "dotdash", "dotted"), length.out = length(levels)), levels), limits = levels),
      ggplot2::scale_shape_manual(values = stats::setNames(c(16, 17, 15, 18, 3, 4, 8, 1)[seq_along(levels)], levels), limits = levels)
    ))
  }
  result
}

.sp_positive <- function(value, name) {
  if (!is.numeric(value) || length(value) != 1 || !is.finite(value) || value <= 0) stop(name, " must be a finite positive number")
  value
}

.sp_pdf_page_mm <- function(path) {
  # Inspect page bounds in this helper's standard R PDF output.
  bytes <- readBin(path, "raw", n = file.info(path)$size)
  ints <- as.integer(bytes)
  ints[ints < 32L | ints > 126L] <- 32L
  text <- rawToChar(as.raw(ints))
  box <- regmatches(text, regexpr("/MediaBox[[:space:]]*\\[[[:space:]]*[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]*\\]", text))
  if (!length(box)) stop("Could not verify PDF page dimensions")
  values <- as.numeric(strsplit(trimws(gsub("/MediaBox|\\[|\\]", "", box)), "[[:space:]]+")[[1]])
  list(width = (values[3] - values[1]) / 72 * 25.4, height = (values[4] - values[2]) / 72 * 25.4)
}

export_scientific <- function(plot, output_stem, formats = c("pdf", "svg", "png"),
                              width_mm = 89, height_mm = 64, dpi = 300,
                              metadata = list(), overwrite = FALSE) {
  width_mm <- .sp_positive(width_mm, "width_mm")
  height_mm <- .sp_positive(height_mm, "height_mm")
  dpi <- .sp_positive(dpi, "dpi")
  if (!length(formats) || anyDuplicated(formats) || any(!formats %in% c("pdf", "svg", "png", "tiff"))) stop("Use unique formats from pdf, svg, png, tiff")
  if ("svg" %in% formats && !requireNamespace("svglite", quietly = TRUE)) stop("Install svglite to export SVG")
  has_ragg <- requireNamespace("ragg", quietly = TRUE)
  if ("tiff" %in% formats && !has_ragg && (!capabilities("tiff") || identical(getOption("bitmapType"), "quartz") && !capabilities("cairo"))) {
    stop("Install ragg for portable LZW TIFF export on this R build")
  }
  targets <- paste0(output_stem, ".", formats)
  manifest <- paste0(output_stem, ".plot.json")
  if (!overwrite && any(file.exists(c(targets, manifest)))) stop("Output exists; use another stem or overwrite = TRUE")
  record <- list(backend = "ggplot2", width_mm = width_mm, height_mm = height_mm, dpi = dpi,
                 formats = formats, metadata = metadata,
                 versions = list(R = as.character(getRversion()), ggplot2 = as.character(utils::packageVersion("ggplot2"))),
                 session = capture.output(utils::sessionInfo()))
  record$raster_device <- if (has_ragg) "ragg" else if (capabilities("cairo")) "cairo" else getOption("bitmapType")
  if (has_ragg) record$versions$ragg <- as.character(utils::packageVersion("ragg"))
  content <- jsonlite::toJSON(record, auto_unbox = TRUE, pretty = TRUE, null = "null", digits = 10)
  dir.create(dirname(output_stem), recursive = TRUE, showWarnings = FALSE)
  stage <- tempfile(pattern = ".plot-", tmpdir = dirname(output_stem))
  dir.create(stage)
  on.exit(unlink(stage, recursive = TRUE), add = TRUE)
  staged <- file.path(stage, basename(targets))
  for (i in seq_along(formats)) {
    fmt <- formats[[i]]
    device <- switch(fmt,
      pdf = function(filename, ...) grDevices::pdf(file = filename, ..., useDingbats = FALSE),
      svg = svglite::svglite,
      png = if (has_ragg) ragg::agg_png else function(...) grDevices::png(..., type = if (capabilities("cairo")) "cairo" else getOption("bitmapType")),
      tiff = function(...) {
        if (has_ragg) ragg::agg_tiff(..., compression = "lzw") else
          grDevices::tiff(..., compression = "lzw", type = if (capabilities("cairo")) "cairo" else getOption("bitmapType"))
      }
    )
    ggplot2::ggsave(filename = staged[[i]], plot = plot, device = device, width = width_mm,
                   height = height_mm, units = "mm", dpi = dpi, limitsize = FALSE)
  }
  if ("pdf" %in% formats) {
    record$pdf_page_mm <- .sp_pdf_page_mm(staged[[match("pdf", formats)]])
    content <- jsonlite::toJSON(record, auto_unbox = TRUE, pretty = TRUE, null = "null", digits = 10)
  }
  staged_manifest <- file.path(stage, basename(manifest))
  writeLines(content, staged_manifest, useBytes = TRUE)
  if (!all(file.exists(c(staged, staged_manifest)))) stop("A graphics device did not create its output; no files published")
  for (i in seq_along(c(targets, manifest))) {
    target <- c(targets, manifest)[[i]]
    if (!overwrite && file.exists(target)) stop("Output appeared during export: ", target)
    if (!file.rename(c(staged, staged_manifest)[[i]], target)) stop("Could not move export to ", target)
  }
  stats::setNames(c(targets, manifest), c(formats, "manifest"))
}
