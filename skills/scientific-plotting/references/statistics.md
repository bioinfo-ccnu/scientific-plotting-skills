# Statistical comparisons

Use the statistical helper only after identifying independent experimental units, subject matching and a defensible test. It does not infer the study design, aggregate technical replicates, remove outliers, or choose a favorable test automatically.

The YAML runner supports brackets on `raincloud` and `paired` panels; the Python `compare_groups` and R `compare_scientific_groups` functions also return a standalone result table. Input needs `group`, `value` and a subject column for paired methods. Each paired subject/group must occur exactly once, with the same subject IDs in each contrasted group. Duplicate or unmatched observations are rejected. Welch tests reject overlapping subject IDs when the subject field is available.

| Method | Test | Reported effect and interval |
|---|---|---|
| `paired-t` | Two-sided paired t test | Mean paired difference, t confidence interval, Cohen's dz |
| `welch-t` | Two-sided Welch t test | Difference in means, Welch t confidence interval, pooled-SD Cohen's d |
| `wilcoxon` | Two-sided signed-rank test | Mean paired difference, percentile bootstrap CI for that **mean difference**, descriptive Cohen's dz |

Effects always mean **second group minus first group** in each contrast. The Wilcoxon p value and bootstrap mean-difference interval describe different inferential quantities; its CI is not a Wilcoxon location-shift interval. Zero-variance data that make the requested inference undefined are rejected. The helper reports group sizes and paired sample size separately.

Set `experimental_unit` explicitly (e.g. independent animal, donor or participant), `method`, `contrasts`, `confidence` (default 0.95), and `adjust` (`bh`, `bonferroni` or `none`). BH and Bonferroni apply across the contrasts in **one panel's comparison call**. They do not automatically correct an entire manuscript, all panels, a family of genes, or upstream differential-expression tests. Group sizes count rows supplied as independent observations; calling technical replicates independent remains an analysis error.

Wilcoxon bootstrap sampling uses `seed` (default 2026) and `bootstrap_samples` (default 2000, minimum 100). Python uses SciPy's Wilcoxon defaults; R uses its normal approximation (`exact=FALSE`). Tied/zero differences can produce backend-specific p values. Seeded bootstrap results are reproducible within the chosen backend/environment; Python and R random generators need not yield identical intervals.

Brackets show the numerical adjusted p value rather than significance stars. The CSV and manifest retain the raw and adjusted p values, correction, confidence bounds, effect sizes, method, group sizes and experimental unit. Explain the direction, uncertainty and correction family in the caption. Inferential results should be checked against the study protocol and assumptions.
