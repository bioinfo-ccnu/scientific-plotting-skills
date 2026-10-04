"""Explicit comparisons: effect sizes, intervals, matching and multiplicity."""
import numpy as np
import pandas as pd
from scipy import stats
from plot_data import require_columns, require_unique


def adjust_pvalues(pvalues, method="bh"):
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1 or not len(p) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("p-values must be a nonempty finite vector in [0,1]")
    if method == "none":
        return p.copy()
    if method == "bonferroni":
        return np.minimum(p * len(p), 1)
    if method == "bh":
        order = np.argsort(p)
        adjusted = np.minimum.accumulate((p[order] * len(p) / np.arange(1, len(p)+1))[::-1])[::-1]
        result = np.empty_like(p)
        result[order] = np.minimum(adjusted, 1)
        return result
    raise ValueError("adjust must be bh, bonferroni or none")


def compare_groups(frame, contrasts, *, method, experimental_unit, subject="subject",
                   confidence=0.95, adjust="bh", seed=2026, bootstrap_samples=2000):
    """Effect direction is second group minus first. No implicit test selection.

    Paired t: mean difference CI and Cohen's dz. Welch: mean difference CI and
    pooled-SD Cohen's d. Wilcoxon: signed-rank p with bootstrap mean-difference CI.
    """
    if not isinstance(experimental_unit, str) or not experimental_unit.strip():
        raise ValueError("Describe the independent experimental_unit")
    if not 0 < confidence < 1 or method not in {"paired-t", "welch-t", "wilcoxon"}:
        raise ValueError("Choose a supported method and confidence in (0,1)")
    if not contrasts:
        raise ValueError("Supply at least one explicit contrast")
    require_columns(frame, ["group", "value"], ["value"])
    result = []
    for contrast in contrasts:
        if len(contrast) != 2 or contrast[0] == contrast[1]:
            raise ValueError("Each contrast must contain two different group names")
        first, second = contrast
        a = frame.loc[frame.group == first]
        b = frame.loc[frame.group == second]
        if min(len(a), len(b)) < 2:
            raise ValueError("Each group needs at least two independent observations")
        if method in {"paired-t", "wilcoxon"}:
            require_columns(frame, [subject])
            require_unique(pd.concat([a, b]), [subject, "group"])
            if set(a[subject]) != set(b[subject]):
                raise ValueError("Paired groups must have exactly matching subject IDs")
            a = a.set_index(subject).sort_index().value.to_numpy()
            b = b.set_index(subject).reindex(sorted(b[subject])).value.to_numpy()
            difference = b - a
            sd = difference.std(ddof=1)
            if sd == 0:
                raise ValueError("Paired differences have zero variance; inferential interval is undefined")
            effect = float(difference.mean())
            standardized = effect / sd
            if method == "paired-t":
                p = float(stats.ttest_rel(b, a).pvalue)
                margin = stats.t.ppf((1+confidence)/2, len(a)-1) * sd / np.sqrt(len(a))
                low, high = effect-margin, effect+margin
                ci_method = "paired-t mean difference"
            else:
                if not isinstance(bootstrap_samples, int) or bootstrap_samples < 100:
                    raise ValueError("bootstrap_samples must be an integer >= 100")
                p = float(stats.wilcoxon(difference).pvalue)
                rng = np.random.default_rng(seed)
                means = rng.choice(difference, (bootstrap_samples, len(difference)), replace=True).mean(axis=1)
                low, high = np.quantile(means, [(1-confidence)/2, (1+confidence)/2])
                ci_method = "percentile bootstrap mean difference"
        else:
            if subject in frame:
                require_columns(frame, [subject])
                require_unique(pd.concat([a, b]), [subject, "group"])
                if set(a[subject]) & set(b[subject]):
                    raise ValueError("Overlapping subject IDs require a paired design, not Welch's independent test")
            a, b = a.value.to_numpy(), b.value.to_numpy()
            v1, v2 = a.var(ddof=1), b.var(ddof=1)
            se2 = v1/len(a) + v2/len(b)
            if se2 == 0:
                raise ValueError("Both groups have zero variance")
            df = se2**2 / ((v1/len(a))**2/(len(a)-1) + (v2/len(b))**2/(len(b)-1))
            effect = float(b.mean()-a.mean())
            pooled = np.sqrt(((len(a)-1)*v1+(len(b)-1)*v2)/(len(a)+len(b)-2))
            standardized = effect / pooled
            p = float(stats.ttest_ind(b, a, equal_var=False).pvalue)
            margin = stats.t.ppf((1+confidence)/2, df) * np.sqrt(se2)
            low, high = effect-margin, effect+margin
            ci_method = "Welch mean difference"
        result.append(dict(first=first, second=second, n_first=len(a), n_second=len(b),
                           effect=effect, ci_low=float(low), ci_high=float(high), confidence=confidence,
                           standardized_effect=float(standardized), standardized_definition="Cohen d" if method == "welch-t" else "Cohen dz",
                           p=p, method=method, ci_method=ci_method, experimental_unit=experimental_unit))
    output = pd.DataFrame(result)
    output["p_adjusted"] = adjust_pvalues(output.p, adjust)
    output["adjustment"] = adjust
    return output


def annotate_comparisons(ax, results, levels):
    """Label the exact adjusted p-value; brackets refer to explicit contrasts."""
    ymin, ymax = ax.get_ylim()
    step = max(ymax-ymin, 1e-6) * 0.12
    for i, row in enumerate(results.itertuples()):
        x1, x2 = levels.index(row.first), levels.index(row.second)
        y = ymax + i*step
        ax.plot([x1, x1, x2, x2], [y, y+step*0.2, y+step*0.2, y], color=ax.xaxis.label.get_color(), linewidth=0.7)
        ax.text((x1+x2)/2, y+step*0.25, f"{row.adjustment} p={row.p_adjusted:.3g}", ha="center", va="bottom", fontsize=7)
    ax.set_ylim(ymin, ymax+(len(results)+0.4)*step)
