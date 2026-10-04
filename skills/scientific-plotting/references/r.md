# R

Core packages: `ggplot2`, `jsonlite`, `svglite`. Add `patchwork` for multi-panel figures and `ragg` for portable raster exports. `ggthemes` and `ggsci` are optional style extensions; `ComplexHeatmap` is useful for annotated omics heatmaps. Install project dependencies rather than changing a global library unnecessarily.

```r
library(ggplot2)
source("/actual/path/to/scientific-plotting/scripts/scientific_style.R")
data <- read.csv("measurements.csv") # columns: group, x, y
levels <- unique(as.character(data$group))
stopifnot(!anyNA(data$group), !anyNA(data$x), !anyNA(data$y))
data$group <- factor(data$group, levels = levels)
p <- ggplot(data, aes(x, y, colour = group)) +
  geom_point(size = 1.4) +
  scientific_scales(levels, "nature") +
  scientific_theme("nature") +
  labs(x = "Time (h)", y = "Response (a.u.)", colour = NULL)
export_scientific(p, "figures/response", width_mm = 89, height_mm = 64,
                  metadata = list(preset = "nature", source = "measurements.csv"))
```

Choose `geom_line()` only for ordered trajectories. For IEEE/accessible figures, map `shape = group` and/or `linetype = group` in `aes()`; the helper supplies matching scales. Confirm all raw group values belong to the chosen global levels **before** converting to factors: factor conversion can turn unexpected values into NA.

Compose with `patchwork::wrap_plots(...)` and specify shared guides, panel tags and layout. Apply `scientific_theme` to each plot and the assembled plot's annotation/background where appropriate. Inspect all labels after composition.

`scientific_theme("minimal") + theme(...)` allows overrides. The presets are original ggplot themes, not a port of upstream SciencePlots source. Export requires the explicit plot object; it does not rely on the last interactive plot. PDF uses the standard R PDF device, SVG uses svglite, and PNG/TIFF prefer ragg (TIFF with LZW compression). Without ragg, supported base devices are used; missing TIFF support is reported before rendering. Width/height are in mm; `dpi` controls raster resolution. Use `formats = c("pdf", "svg", "png", "tiff")` for all exports.

Generic `sans`/`serif` fonts are portable across devices but not guaranteed identical on every OS. For custom/CJK fonts, verify device support. A Cairo PDF device may be appropriate when `capabilities("cairo")` is true; adapt the export helper in the project if embedding a custom font is required. SVG retains text and therefore needs the font at viewing time. Do not use showtext indiscriminately when editable text is required.

The standard R PDF device floors its page box to whole points. `width_mm` and `height_mm` in the manifest are the requested canvas; `pdf_page_mm` contains measured PDF bounds. The rounding error is less than 0.353 mm per dimension. SVG is precise within decimal rounding. If sub-point PDF precision is explicitly required, verify a conversion from the SVG with the user's approved tools and check fonts and page dimensions afterward; do not silently promise exact R PDF bounds.

Official references: [ggplot2 themes](https://ggplot2.tidyverse.org/reference/theme.html), [ggsave](https://ggplot2.tidyverse.org/reference/ggsave.html), [patchwork](https://patchwork.data-imaginist.com/), [ComplexHeatmap](https://jokergoo.github.io/ComplexHeatmap-reference/book/).
