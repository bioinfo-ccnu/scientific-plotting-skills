# Configuration, data and batch jobs

Run the installed skill's helpers with either backend:

```bash
python /path/to/skill/scripts/plot_cli.py job.yml
python /path/to/skill/scripts/plot_cli.py job.yml --backend r
Rscript /path/to/skill/scripts/plot_cli.R job.yml
```

The Python dispatcher needs the core Python dependencies even when dispatching to R. Direct `Rscript` execution needs no Python. Locate scripts relative to this skill's installed folder. The repository contains ready-to-run jobs in `examples/configs/`; the installable folder contains CSV/Excel templates in `assets/templates/`.

Install recipe dependencies in the selected project environment. A standalone installed skill can use these commands; a repository checkout also provides `requirements.txt`:

```bash
python -m pip install 'matplotlib>=3.8,<3.13' 'SciencePlots>=2.1,<3' \
  'numpy>=1.26,<3' 'pandas>=2.1,<4' 'scipy>=1.11,<2' \
  'scikit-learn>=1.4,<2' 'networkx>=3,<4' 'openpyxl>=3.1,<4' \
  'PyYAML>=6,<7' 'Pillow>=10,<13'
```

```r
install.packages(c("ggplot2", "patchwork", "jsonlite", "yaml", "readxl",
                   "xml2", "systemfonts", "svglite", "ragg"))
```

```yaml
version: 1
backend: python
presets: [nature, dark]
output: figures/comparison
width_mm: 180
height_mm: 100
dpi: 300
formats: [pdf, svg, png]
title: Paired treatment measurements
category_levels: [Control, Treatment]
layout:
  ncols: 1
  tags: true
panels:
  - type: paired
    data: measurements.csv
    columns: {subject: participant, group: condition, value: response}
    options: {title: Response, ylabel: Response (a.u.)}
    statistics:
      method: paired-t
      experimental_unit: independent participant
      contrasts: [[Control, Treatment]]
      confidence: 0.95
      adjust: bh
```

Only use these statistical settings after verifying the experimental design and assumptions. Set `synthetic: true` for demonstrations and visibly label them. This flag records provenance; it does not generate data or add the label automatically.

## Inputs and field mapping

- CSV, TSV and Excel (`.xlsx`, `.xlsm`) are supported. Use `sheet: Measurements` or a **zero-based** numeric sheet index in YAML for both backends. The standalone R loading function itself follows readxl's one-based numeric convention.
- `columns` maps **canonical recipe name → source column name**. Mapping occurs before reshaping. Missing source names, ambiguous renames and duplicate keys are rejected.
- Paths in `data` and YAML `output` are relative to the configuration file. `--output STEM` is relative to the command's working directory. Absolute paths are accepted.
- Long reshape: `reshape: {mode: long, id_columns: [subject], value_columns: [A, B], names_to: group, values_to: value}`. This turns wide paired measurements into one observation per subject/group.
- Wide reshape: `reshape: {mode: wide, index: [subject], columns: group, values: value}`. Duplicate index/name combinations are rejected; no implicit averaging occurs. Recipes usually consume long tables.
- Required numeric data must be finite. Matrix recipes require a complete rectangular matrix; paired plots require complete matching subject IDs. Clean or resolve missing data explicitly upstream.

## Layout and style batches

`preset` selects one style; `presets` generates several. Output names append the preset, e.g. `comparison-nature.pdf`. Category colors are assigned once per style across panels. Set `category_levels` to control their order; otherwise the runner uses first appearance across input tables. Palette capacity is finite; choose a suitable preset or custom source for more categories.

`layout` accepts `ncols`, `tags`, custom `labels`, `shared_legend`, `sharex` and `sharey`. Tags default to A, B, C…; supply one custom label per panel. Share axes only for panels with compatible measurements and units. R explicitly supports shared limits for ribbon/facet/prediction/UMAP x axes and those plus raincloud/paired y axes. Other R recipes require explicit limits. A shared legend is useful for compatible scales with identical semantics; the Python runner deduplicates legend labels and R patchwork collects equivalent guides. For example, raincloud and paired panels can keep two legends because their guide glyphs differ. `shared_legend` does not guarantee one legend for every combination of plot types. Legends inside compound recipes remain local.

Each panel's `options` can set `title`, `xlabel`, `ylabel`, `xlim`, `ylim`, plus recipe-specific settings. Ribbon, prediction and UMAP support `inset: {xlim: [0.2, 0.5], ylim: [0.2, 0.5], bounds: [0.55, 0.12, 0.4, 0.4]}`; bounds are normalized panel coordinates. The inset reuses the same data, style and category colors. Do not add statistical annotations to a zoomed subset as though it were a new experiment.

## Export and reproduction

Defaults: 180 × 120 mm, 300 dpi, PDF/SVG/PNG. TIFF is available. Existing figure files and sidecars are protected; use `--overwrite` only for intended replacement. All requested styles/formats render in staging before publication; a late validation/rendering failure does not publish an early style. Concurrent writers should use separate stems; moving a group of files is not a filesystem transaction.

Each style produces the figures, `*.plot.json`, `*.qc.json`, a resolved `*.config.yml`, and a runnable `*.source.py` or `*.source.R`. Statistics add `*.statistics.csv`. Source wrappers use the installed helpers:

```bash
python comparison-nature.source.py /path/to/skill/scripts
Rscript comparison-nature.source.R /path/to/skill/scripts
```

The wrappers explicitly replace their batch outputs. They rerun the resolved configuration, which may list several presets. Keep its referenced input files available, along with the skill version and dependency environment. Python records SHA-256 input/config hashes; R records MD5 hashes. Hashes identify input bytes, not data validity. Metrics, clustering choices, interval definitions, category colors, statistical results and environment versions are recorded in the manifest. The R PDF page box has the documented whole-point rounding; inspect measured dimensions in the manifest.
