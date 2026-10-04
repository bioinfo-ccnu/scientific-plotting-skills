# Recipe galleries

All figures use **synthetic data** (seed 2026), provided as [input templates](../../skills/scientific-plotting/assets/templates). These are plotting demonstrations, not research results. Python and R use the same inputs and preset palettes; graphics devices, ticks, network layouts, density estimates and clustering tie order can differ.

Run [recipe_gallery.py](../recipe_gallery.py) with `--backend python` or `--backend r`. Each category has a YAML job in [configs](../configs); individual jobs cover all 22 recipes. Vector PDF/SVG exports, provenance/metrics manifests, resolved configurations, source wrappers and heuristic QA reports are generated at runtime. The committed category previews use 180 dpi; vector files retain scalable content. Select 300 dpi or your actual destination requirement for final raster figures.

## Reading the panels

- **General A–F:** raincloud (every observation, median/quartiles/1.5×IQR box), matched subject pairs, a supplied synthetic ±0.06 ribbon, supplied synthetic forest intervals, Pearson correlation, and grouped facets. The ribbon/forest intervals are illustrative supplied ranges, not inferred confidence intervals.
- **Bioinformatics A–E:** volcano and MA from supplied adjusted p values (display cutoffs q≤0.05 and |log2FC|≥1), supplied pathway summaries, exact membership intersections, and an average-linkage/Euclidean clustered matrix centered on zero. Annotation strips use the labeled A/B groups; their mapping is in the input and manifest. No differential-expression or enrichment analysis is run.
- **Evaluation A–G:** ROC, PR, confusion, calibration, observed/predicted with zoom, ablation and raw-unit metric facets. Binary truth uses positive class 1; models A/B/C have 60 supplied observations each, 30 positive. AUROC, average precision and Brier score are calculated; PR dashed baselines show prevalence. Calibration uses 10 uniform bins. This synthetic example is not evidence of model performance.
- **Network/single-cell A–D:** supplied topology, hierarchical clustering of a supplied matrix, supplied UMAP-like coordinates, and supplied expression summaries. No embedding or single-cell analysis is computed. Dot area shows expressing fraction; color shows the supplied synthetic mean expression.

Automatic reports may request review for small compound-panel text, estimated overlap/contrast, the preview DPI and R's whole-point PDF rounding. They are intentionally not treated as certification; review actual final-size outputs. The README links the [QA limits](../../skills/scientific-plotting/references/automation-quality.md).


## General

| Style | Python | R |
|---|---|---|
| `nature` | ![Python general synthetic](python-general-nature.png) | ![R general synthetic](r-general-nature.png) |
| `dark` | ![Python general synthetic](python-general-dark.png) | ![R general synthetic](r-general-dark.png) |

## Bioinformatics

| Style | Python | R |
|---|---|---|
| `nature` | ![Python bioinformatics synthetic](python-bioinformatics-nature.png) | ![R bioinformatics synthetic](r-bioinformatics-nature.png) |
| `dark` | ![Python bioinformatics synthetic](python-bioinformatics-dark.png) | ![R bioinformatics synthetic](r-bioinformatics-dark.png) |

## Evaluation

| Style | Python | R |
|---|---|---|
| `nature` | ![Python evaluation synthetic](python-evaluation-nature.png) | ![R evaluation synthetic](r-evaluation-nature.png) |
| `dark` | ![Python evaluation synthetic](python-evaluation-dark.png) | ![R evaluation synthetic](r-evaluation-dark.png) |

## Network Single Cell

| Style | Python | R |
|---|---|---|
| `nature` | ![Python network-single-cell synthetic](python-network-single-cell-nature.png) | ![R network-single-cell synthetic](r-network-single-cell-nature.png) |
| `dark` | ![Python network-single-cell synthetic](python-network-single-cell-dark.png) | ![R network-single-cell synthetic](r-network-single-cell-dark.png) |

## Shared panel controls

[shared-panels.yml](../configs/shared-panels.yml) demonstrates consistent colors, shared axes and a collected legend for equivalent ribbon guides. Zoom examples are in [prediction.yml](../configs/prediction.yml). Compound recipes retain local legends.

| Python | R |
|---|---|
| ![Python shared panels](shared-python-nature.png) | ![R shared panels](shared-r-nature.png) |

## Optional adapters

These synthetic demonstrations exercise the actual optional packages. See [source](../domain_adapters.R) and [Python source](../domain_adapters.py), with [adapter documentation](../../skills/scientific-plotting/references/domain-adapters.md). The ComplexHeatmap preview displays the synthetic matrix; its source and manifest mark it as synthetic.

| ComplexHeatmap | ggraph | Scanpy |
|---|---|---|
| ![Synthetic ComplexHeatmap](adapter-complex-heatmap.png) | ![Synthetic ggraph](adapter-ggraph-network.png) | ![Synthetic existing Scanpy embedding](adapter-scanpy-umap.png) |
