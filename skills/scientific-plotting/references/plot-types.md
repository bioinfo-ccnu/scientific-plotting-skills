# Plot choices and scientific semantics

| Question/data | Useful plots | Checks that change the interpretation |
|---|---|---|
| Ordered time/dose or convergence | Lines, points, uncertainty ribbons | Sort x within a series; identify replicates; define ribbon coverage; use log axes only for suitable values |
| Distribution or group comparison | Raw points with box/violin or interval summaries | Show observations when feasible; identify n and experimental unit; disclose exclusion rules; avoid mean-only bars |
| Association | Scatter, density for large n, optional fitted curve | Do not treat repeated measurements as independent; define correlation/fitting method and uncertainty |
| Signed effects and uncertainty | Forest plot | Identify effect scale, reference line, interval type and confidence level; transform intervals consistently |
| Model discrimination | ROC and PR curves | Use held-out predictions; specify positive class; include prevalence for PR and appropriate baselines; never fabricate AUC/CI |
| Counts or proportions | Dot/bar, stacked proportions when justified | Bars normally start at zero; report denominator; distinguish counts from normalized values |
| Matrices and omics | Heatmap with annotations | State normalization and distance/linkage; keep color limits comparable; distinguish missing values; center signed maps meaningfully |
| Differential analysis | Volcano / MA | Require actual effect sizes and p/q values; distinguish p from adjusted p; document thresholds and zeros; do not invent significance |
| Enrichment | Dot/interval plots | Show adjusted p and effect/enrichment metric distinctly; identify tested background and gene-set version |
| Biomolecular scores | Scatter, distributions, ranked intervals | State direction and units (e.g. docking energy); distinguish calculated scores from experimentally measured binding |

These are routing decisions, not fixed chart templates. For specialized visualizations (sequence logos, contact maps, RNA structures, molecular surfaces), choose a maintained domain library and verify its current API. A schematic molecular drawing is not evidence of a computed structure.

For heatmaps, preserve row/column IDs in source data and disclose clustering. For multi-panel biological figures, synchronize the same treatment/model colors across every panel. Supply a caption that defines abbreviations and encodings; caption claims must be supported by the plotted data.
