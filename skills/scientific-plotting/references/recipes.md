# Runnable recipe catalog

All 22 recipes have Python and R implementations, input validation and a synthetic CSV template. Use `draw_recipe(type, dataframe, axes, preset="nature", options={...})` in Python or `draw_scientific_recipe(type, data, preset="nature", options=list(...))` in R after sourcing `plot_cli.R`. The Python function draws on the supplied axes and returns a report; R returns `list(plot, report)`. The YAML runner handles composition, exports and QA.

| Recipe | Required columns | Synthetic template |
|---|---|---|
| `raincloud` | `group`, `value` | [raincloud.csv](../assets/templates/raincloud.csv) |
| `paired` | `subject`, `group`, `value` | [paired.csv](../assets/templates/paired.csv) |
| `ribbon` | `group`, `x`, `mean`, `lower`, `upper` | [ribbon.csv](../assets/templates/ribbon.csv) |
| `forest` | `label`, `effect`, `lower`, `upper` | [forest.csv](../assets/templates/forest.csv) |
| `correlation` | `sample`, `feature`, `value` | [correlation.csv](../assets/templates/correlation.csv) |
| `facet` | `facet`, `group`, `x`, `y` | [facet.csv](../assets/templates/facet.csv) |
| `volcano` | `label`, `log2fc`, `q` | [volcano.csv](../assets/templates/volcano.csv) |
| `ma` | `label`, `mean_expression`, `log2fc`, `q` | [ma.csv](../assets/templates/ma.csv) |
| `enrichment` | `term`, `ratio`, `count`, `q` | [enrichment.csv](../assets/templates/enrichment.csv) |
| `upset` | `item`, `set` | [upset.csv](../assets/templates/upset.csv) |
| `heatmap` | `row`, `column`, `value` | [heatmap.csv](../assets/templates/heatmap.csv) |
| `roc` | `model`, `truth`, `score` | [roc.csv](../assets/templates/roc.csv) |
| `pr` | `model`, `truth`, `score` | [pr.csv](../assets/templates/pr.csv) |
| `confusion` | `truth`, `prediction` | [confusion.csv](../assets/templates/confusion.csv) |
| `calibration` | `model`, `truth`, `score` | [calibration.csv](../assets/templates/calibration.csv) |
| `prediction` | `model`, `observed`, `predicted` | [prediction.csv](../assets/templates/prediction.csv) |
| `ablation` | `model`, `component`, `value` | [ablation.csv](../assets/templates/ablation.csv) |
| `benchmark` | `model`, `metric`, `value` | [benchmark.csv](../assets/templates/benchmark.csv) |
| `network` | `source`, `target` | [network.csv](../assets/templates/network.csv) |
| `dendrogram` | `sample`, `feature`, `value` | [dendrogram.csv](../assets/templates/dendrogram.csv) |
| `umap` | `cell`, `group`, `umap1`, `umap2` | [umap.csv](../assets/templates/umap.csv) |
| `dotplot` | `group`, `gene`, `mean_expression`, `fraction` | [dotplot.csv](../assets/templates/dotplot.csv) |

## Scientific contracts and options

- **Raincloud / paired:** raw observations remain visible. Raincloud combines density, box and jittered points. Paired connects complete matching subject IDs and reports the number of pairs. A box describes quartiles/median with 1.5 × IQR whiskers, not a confidence interval.
- **Ribbon / forest:** supply `interval_definition` (e.g. 95% CI, SD or a clearly described illustrative range). Bounds must enclose the supplied mean/effect. No interval is inferred from summary values.
- **Correlation / dendrogram:** long-form matrices must be complete with unique sample/feature keys. Correlation supports `correlation: pearson` or `spearman` and rejects constant variables. Clustering defaults to average linkage/Euclidean distance; `linkage: ward` requires Euclidean distance. No automatic normalization occurs.
- **Facet:** supplied facet/group/x/y data; at most six facets per compound panel. **Benchmark:** metric/model/value data appear in separate metric axes with their original units; no silent normalization or conversion of metrics to a common score.
- **Volcano / MA:** `q` means a supplied adjusted p value in [0,1], not raw p. Default cutoffs `q_threshold: 0.05`, `effect_threshold: 1` are configurable display rules. Zero q requires explicit `q_floor` for log display; original q is preserved. MA requires positive mean expression. These functions do not run differential expression or FDR correction.
- **Enrichment:** supplied GO/KEGG or other terms, ratio [0,1], positive integer count and adjusted p. Bubble area represents count; color represents −log10(q). No enrichment analysis is performed.
- **UpSet:** one membership row per item/set, no duplicates. Intersections are exact memberships rather than inclusive pairwise overlaps. `max_intersections` defaults to 12; the manifest records all intersection counts and the number of items shown when truncated.
- **Heatmap:** complete unique row/column/value matrix; optional consistent `row_group,column_group`. `cluster_rows` and `cluster_columns` default true. Specify `center: 0` for signed data and a symmetric diverging scale. Clustering and annotation order are recorded. Core recipes reorder the matrix; use the ComplexHeatmap adapter when visible dendrograms and richer annotations are needed.
- **ROC / PR / calibration:** truth must be 0 or 1 with both classes per model; score must be in [0,1] for the positive class 1. Optional `sample` IDs enforce uniqueness per model/sample. AUROC, average precision (not trapezoidal PR AUC), prevalence and Brier score are calculated from the supplied observations. PR displays prevalence baselines. Calibration uses uniform bins (`bins`, default 10); empty bins are omitted. Compare models on the same held-out units; these helpers cannot detect data leakage or infer a valid split.
- **Confusion:** supplied truth/prediction classes, counts and accuracy. Use `class_levels` for order; it must include all observed classes. **Prediction:** supplied observed/predicted pairs; reports RMSE, MAE and R² where defined. **Ablation:** supplied component/model/value points; no invented replicate variation or significance.
- **Network:** unique source/target edges with `directed` optional; reciprocal duplicates are rejected for undirected graphs. Core Python supports `layout: spring` or `circular`, core R uses circular. Seed defaults 2026; weights do not influence layout. **UMAP:** unique cell IDs and supplied coordinates only; no embedding computation.
- **DotPlot:** supplied group/gene mean expression and fraction [0,1]. Dot area shows expressing fraction and color shows mean expression. Supply normalization and expression-threshold definitions in the caption. No counts-to-expression or differential analysis is performed.

See [configuration](configuration.md), [statistics](statistics.md) and [optional domain adapters](domain-adapters.md) for the relevant mode. Templates are synthetic examples; replace them with your own data without treating their values as experimental results.
