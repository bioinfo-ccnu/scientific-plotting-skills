---
name: scientific-plotting
description: Create, restyle, and export scientific figures and multi-panel research plots in Python or R, with reproducible source code, flexible visual styles, and figure quality checks. Use for data-driven research figures; not for dashboards or illustrative artwork.
---

# Scientific Plotting

Turn research data into clear, reproducible figures. Support Python with Matplotlib, SciencePlots and Seaborn, or R with ggplot2 and patchwork. The helpers provide shared palettes, configurable styles and explicit-size exports; they do not restrict which scientific plots can be created.

## Select the approach

- Honor the requested language, existing project conventions, visual reference and output formats. If no backend is specified, infer it from the project and runtime, state the choice, and proceed. Ask only when the choice materially changes the result.
- Establish the intended message, data schema, units, independent observations, uncertainty definition, and required dimensions. Inspect supplied data before selecting a plot. Continue useful work while resolving missing details.
- For a real result, use supplied data or an identified source. Never invent measurements, significance, uncertainty, sample sizes or model performance. Label demonstration data and figures as synthetic.

## Implement

Read only the relevant references:

- **Python:** [references/python.md](references/python.md), including SciencePlots registration and optional LaTeX.
- **R:** [references/r.md](references/r.md), including ggplot2 themes and patchwork assembly.
- **Style selection:** [references/styles.md](references/styles.md). Presets are starting points; user choices take precedence.
- **Runnable recipes and data schemas:** [references/recipes.md](references/recipes.md), with 22 paired Python/R implementations and synthetic CSV templates.
- **CSV/Excel, YAML batches and multi-panel assembly:** [references/configuration.md](references/configuration.md). Use the configuration runner for repeatable jobs, or the recipe functions when custom source is more useful.
- **Statistical annotations:** [references/statistics.md](references/statistics.md). Require the experimental unit and explicitly chosen test before calculating significance.
- **ComplexHeatmap, ggraph or existing AnnData embeddings:** [references/domain-adapters.md](references/domain-adapters.md). These are optional adapters, not analysis pipelines.
- **Plot-specific decisions:** [references/plot-types.md](references/plot-types.md), especially uncertainty, heatmaps, model evaluation and bioinformatics plots.

Import `scripts/scientific_style.py` or source `scripts/scientific_style.R` when their helpers fit. Locate them relative to this skill folder, not a workstation path. Both read `assets/style-presets.json`. Read function signatures when adapting the helpers. Install only dependencies needed by the selected backend in a project environment.

Preserve category-to-color mappings across panels and use redundant encodings where color alone is insufficient. Keep raw observations, outliers and axis transformations scientifically defensible. Define error bars in the legend or caption; do not silently substitute SEM for SD or CI. Distinguish independent samples from technical replicates. Report a statistical method only if actually applied to appropriate data.

## Review and deliver

Read [references/quality.md](references/quality.md) for final-size review and exports, and [references/automation-quality.md](references/automation-quality.md) when using automated QA. A `pass` is a heuristic result; inspect the rendered figure before delivery. Render and inspect the actual figure: check overlap, clipping, contrast, labels, units, category consistency and visible uncertainty. Correct observed problems and render again.

Provide the figure, editable plotting source, input or source-data reference, and export metadata. Default to vector PDF/SVG plus a PNG preview when useful; honor requested formats. Save raster files at an appropriate explicit resolution and preserve physical dimensions. Overwrite existing outputs only when the user requests replacement. Identify remaining limitations precisely.

Journal-named presets approximate visual conventions. They do not certify compliance; consult the target journal's current instructions when a submission specification is requested.
