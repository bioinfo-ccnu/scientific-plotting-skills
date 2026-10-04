"""Composable scientific recipes. All transformations/metrics are returned."""
from itertools import combinations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import TwoSlopeNorm, Normalize
from scipy.cluster.hierarchy import linkage, leaves_list, dendrogram
from sklearn import metrics
from sklearn.calibration import calibration_curve
import networkx as nx
from plot_data import require_columns, require_unique
from scientific_style import category_colors

CATALOG = json.loads((Path(__file__).resolve().parents[1] / "assets/recipe-catalog.json").read_text())
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
LINES = ["-", "--", "-.", ":"]


def _levels(frame, column, options):
    observed = list(dict.fromkeys(frame[column].astype(str)))
    levels = options.get("levels", observed)
    if not isinstance(levels, list) or not levels or len(set(levels)) != len(levels):
        raise ValueError("levels must be a nonempty list of unique strings")
    if not set(observed) <= set(levels):
        raise ValueError(f"Unmapped categories: {set(observed)-set(levels)}")
    return levels


def _probability(values, name):
    if ((values < 0) | (values > 1)).any():
        raise ValueError(f"{name} must be in [0,1]")


def _qlog(q, options):
    _probability(q, "q")
    if (q == 0).any() and "q_floor" not in options:
        raise ValueError("Zero q-values need an explicit q_floor for log display")
    floor = options.get("q_floor", np.finfo(float).tiny)
    if not 0 < floor <= 1:
        raise ValueError("q_floor must be in (0,1]")
    return -np.log10(np.maximum(q, floor))


def matrix_data(frame, row, column, value):
    require_unique(frame, [row, column])
    matrix = frame.pivot(index=row, columns=column, values=value)
    if matrix.isna().any().any():
        raise ValueError("Matrix is incomplete; resolve missing cells explicitly")
    return matrix


def classification_data(frame):
    _probability(frame.score, "score")
    if set(frame.truth) != {0, 1}:
        raise ValueError("Binary truth must contain both 0 and 1; 1 is the positive class")


def classification_metrics(frame):
    require_columns(frame, ["truth", "score"], ["truth", "score"])
    classification_data(frame)
    return dict(n=len(frame), positives=int(frame.truth.sum()), prevalence=float(frame.truth.mean()),
                auroc=float(metrics.roc_auc_score(frame.truth, frame.score)),
                average_precision=float(metrics.average_precision_score(frame.truth, frame.score)),
                brier=float(metrics.brier_score_loss(frame.truth, frame.score)))


def intersection_counts(frame):
    require_unique(frame, ["item", "set"])
    memberships = frame.groupby("item", sort=False)["set"].agg(lambda x: tuple(sorted(map(str, x))))
    return memberships.value_counts().sort_values(ascending=False)


def draw_recipe(kind, frame, ax, *, preset="science", options=None):
    """Draw on an existing axis. Returns metrics and operation disclosures.

    No significance tests occur here. Inference is an explicit statistics task.
    """
    options = dict(options or {})
    if kind not in CATALOG:
        raise ValueError(f"Unknown recipe {kind}; choose {', '.join(CATALOG)}")
    schema = CATALOG[kind]
    require_columns(frame, schema["columns"], schema["numeric"])
    frame = frame.copy()
    report = {"recipe": kind, "n_rows": len(frame)}
    group_column = "model" if "model" in schema["columns"] else "group" if "group" in schema["columns"] else None
    if group_column:
        frame[group_column] = frame[group_column].astype(str)
        levels = _levels(frame, group_column, options)
        colors = options.get("colors") or category_colors(levels, preset)
        if not set(levels) <= set(colors):
            raise ValueError("colors must cover every configured level")
        report["category_colors"] = colors
    if kind == "raincloud":
        for i, group in enumerate(levels):
            values = frame.loc[frame.group == group, "value"].to_numpy()
            if not len(values):
                continue
            if len(values) >= 3 and np.std(values) > 0:
                violin = ax.violinplot(values, positions=[i-0.14], widths=0.6, showextrema=False)
                for body in violin["bodies"]:
                    body.set_facecolor(colors[group]); body.set_alpha(0.3)
                    vertices = body.get_paths()[0].vertices
                    vertices[:, 0] = np.minimum(vertices[:, 0], i-0.14)
            ax.boxplot([values], positions=[i], widths=0.12, showfliers=False,
                       boxprops={"color": colors[group]}, medianprops={"color": colors[group]},
                       whiskerprops={"color": colors[group]}, capprops={"color": colors[group]})
            jitter = np.random.default_rng(options.get("seed", 2026)+i).uniform(0.14, 0.32, len(values))
            ax.scatter(i+jitter, values, c=colors[group], s=10, marker=MARKERS[i], alpha=0.8)
            ax.text(i, 0.98, f"n={len(values)}", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=7)
        ax.set(xticks=range(len(levels)), xticklabels=levels, ylabel="Value")
    elif kind == "paired":
        require_unique(frame, ["subject", "group"])
        wide = frame.pivot(index="subject", columns="group", values="value").reindex(columns=levels)
        if wide.isna().any().any():
            raise ValueError("Paired plot needs complete subject IDs at every condition")
        for row in wide.to_numpy():
            ax.plot(range(len(levels)), row, color=ax.xaxis.label.get_color(), alpha=0.25, linewidth=0.7)
        for i, group in enumerate(levels):
            ax.scatter(np.full(len(wide), i), wide[group], c=colors[group], marker=MARKERS[i], s=15, label=group)
        ax.set(xticks=range(len(levels)), xticklabels=levels, ylabel="Value")
        report["n_pairs"] = len(wide)
    elif kind == "ribbon":
        if not options.get("interval_definition"):
            raise ValueError("ribbon requires interval_definition (e.g. 95% CI or SD)")
        require_unique(frame, ["group", "x"])
        if ((frame.lower > frame["mean"]) | (frame["mean"] > frame.upper)).any():
            raise ValueError("Intervals must satisfy lower <= mean <= upper")
        for i, group in enumerate(levels):
            data = frame.loc[frame.group == group].sort_values("x")
            ax.plot(data.x, data["mean"], color=colors[group], linestyle=LINES[i%4], label=group)
            ax.fill_between(data.x, data.lower, data.upper, color=colors[group], alpha=0.18)
        ax.set(xlabel="x", ylabel="Mean")
        ax.legend(frameon=False)
        report["interval_definition"] = options["interval_definition"]
    elif kind == "forest":
        if not options.get("interval_definition"):
            raise ValueError("forest requires interval_definition")
        require_unique(frame, ["label"])
        if ((frame.lower > frame.effect) | (frame.effect > frame.upper)).any():
            raise ValueError("Intervals must contain the effect estimate")
        ax.errorbar(frame.effect, range(len(frame)), xerr=[frame.effect-frame.lower, frame.upper-frame.effect], fmt="o", capsize=2)
        ax.axvline(options.get("reference", 0), color="gray", linestyle="--", linewidth=0.8)
        ax.set(yticks=range(len(frame)), yticklabels=frame.label, xlabel="Effect")
        ax.invert_yaxis()
        report["interval_definition"] = options["interval_definition"]
    elif kind in {"correlation", "dendrogram"}:
        matrix = matrix_data(frame, "sample", "feature", "value")
        if len(matrix) < 3:
            raise ValueError("At least three samples are required")
        if kind == "dendrogram":
            method, metric = options.get("linkage", "average"), options.get("distance", "euclidean")
            if method == "ward" and metric != "euclidean":
                raise ValueError("Ward linkage requires Euclidean distance")
            dendrogram(linkage(matrix, method=method, metric=metric), labels=matrix.index.astype(str).tolist(), ax=ax)
            ax.set(ylabel=f"{metric} distance")
            report.update(linkage=method, distance=metric)
        else:
            method = options.get("correlation", "pearson")
            if method not in {"pearson", "spearman"}:
                raise ValueError("correlation must be pearson or spearman")
            correlation = matrix.corr(method=method)
            if not np.isfinite(correlation.to_numpy()).all():
                raise ValueError("Constant columns produce undefined correlations")
            image = ax.imshow(correlation, vmin=-1, vmax=1, cmap="RdBu_r")
            ax.set(xticks=range(len(correlation)), xticklabels=correlation.columns,
                   yticks=range(len(correlation)), yticklabels=correlation.index)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
            ax.figure.colorbar(image, ax=ax, label=f"{method} r", shrink=0.75)
            report["method"] = method
    elif kind in {"facet", "benchmark"}:
        facet_column = "facet" if kind == "facet" else "metric"
        facets = list(dict.fromkeys(frame[facet_column].astype(str)))
        if len(facets) > 6:
            raise ValueError("Split more than six facets into separate figures")
        ax.set_axis_off()
        for i, facet in enumerate(facets):
            ncols = min(2, len(facets)); nrows = int(np.ceil(len(facets)/ncols))
            child = ax.inset_axes([i%ncols/ncols+0.09, 1-(i//ncols+1)/nrows+0.13, 0.8/ncols, 0.7/nrows])
            data = frame.loc[frame[facet_column].astype(str) == facet]
            for j, group in enumerate(levels):
                subset = data.loc[data[group_column] == group]
                if kind == "facet":
                    child.scatter(subset.x, subset.y, s=9, color=colors[group], marker=MARKERS[j])
                else:
                    child.scatter(subset.value, np.full(len(subset), j), s=15, color=colors[group], marker=MARKERS[j])
            child.set_title(facet, fontsize=8)
            if kind == "benchmark":
                child.set(yticks=range(len(levels)), yticklabels=levels, xlabel=facet)
            else:
                child.set(xlabel="x", ylabel="y")
            child.tick_params(labelsize=6)
        if kind == "benchmark":
            require_unique(frame, ["model", "metric"])
        report["facets"] = facets
    elif kind in {"volcano", "ma"}:
        require_unique(frame, ["label"])
        logq = _qlog(frame.q.to_numpy(), options)
        threshold, effect_threshold = options.get("q_threshold", 0.05), options.get("effect_threshold", 1)
        if not 0 < threshold <= 1 or effect_threshold < 0:
            raise ValueError("Invalid significance/effect threshold")
        selected = (frame.q <= threshold) & (frame.log2fc.abs() >= effect_threshold)
        status = np.where(selected & (frame.log2fc > 0), "Up", np.where(selected, "Down", "Other"))
        color_map = {"Up": "#D55E00", "Down": "#0072B2", "Other": "#999999"}
        if kind == "ma" and (frame.mean_expression <= 0).any():
            raise ValueError("MA log x-axis requires positive mean_expression")
        x = frame.log2fc if kind == "volcano" else frame.mean_expression
        y = logq if kind == "volcano" else frame.log2fc
        for group in ("Other", "Down", "Up"):
            mask = status == group
            ax.scatter(x[mask], y[mask], s=10, color=color_map[group], alpha=0.75, label=f"{group} (n={mask.sum()})")
        if kind == "volcano":
            ax.axhline(-np.log10(threshold), color="gray", linestyle="--", linewidth=0.6)
            for bound in [-effect_threshold, effect_threshold]:
                ax.axvline(bound, color="gray", linestyle="--", linewidth=0.6)
            ax.set(xlabel="log2 fold change", ylabel="−log10 adjusted p")
        else:
            ax.set_xscale("log"); ax.axhline(0, color="gray", linewidth=0.6)
            ax.set(xlabel="Mean expression", ylabel="log2 fold change")
        ax.legend(frameon=False, fontsize=6)
        report.update(q_threshold=threshold, effect_threshold=effect_threshold, q_floor=options.get("q_floor"), zero_q=int((frame.q == 0).sum()))
    elif kind == "enrichment":
        require_unique(frame, ["term"])
        logq = _qlog(frame.q.to_numpy(), options)
        if ((frame.ratio < 0) | (frame.ratio > 1) | (frame["count"] <= 0) | (frame["count"] % 1 != 0)).any():
            raise ValueError("ratio must be in [0,1] and count a positive integer")
        image = ax.scatter(frame.ratio, range(len(frame)), s=frame["count"]/frame["count"].max()*120,
                           c=logq, cmap="viridis", edgecolors="gray", linewidth=0.3)
        ax.set(yticks=range(len(frame)), yticklabels=frame.term, xlabel="Gene ratio")
        ax.invert_yaxis()
        ax.figure.colorbar(image, ax=ax, label="−log10 adjusted p", shrink=0.75)
        sizes = sorted(set([int(frame["count"].min()), int(frame["count"].max())]))
        handles = [ax.scatter([], [], s=n/frame["count"].max()*120, color="gray", label=str(n)) for n in sizes]
        ax.legend(handles=handles, title="Count", frameon=False, fontsize=6, title_fontsize=7)
    elif kind == "upset":
        counts = intersection_counts(frame)
        maximum = options.get("max_intersections", 12)
        if not isinstance(maximum, int) or maximum < 1:
            raise ValueError("max_intersections must be a positive integer")
        counts = counts.iloc[:maximum]
        sets = sorted(frame["set"].astype(str).unique())
        top = ax.inset_axes([0.20, 0.44, 0.78, 0.54]); bottom = ax.inset_axes([0.20, 0.05, 0.78, 0.31])
        ax.set_axis_off()
        top.bar(range(len(counts)), counts.to_numpy(), color="#0072B2")
        top.set(ylabel="Intersection size", xticks=[])
        for x, membership in enumerate(counts.index):
            bottom.scatter(np.full(len(sets), x), range(len(sets)), c="#CCCCCC", s=8)
            indices = [sets.index(s) for s in membership]
            bottom.plot(np.full(len(indices), x), indices, "o-", color="#202020", markersize=3, linewidth=0.8)
        bottom.set(yticks=range(len(sets)), yticklabels=sets, xticks=[], ylim=(-0.5, len(sets)-0.5), xlim=top.get_xlim())
        top.tick_params(labelsize=6); bottom.tick_params(labelsize=6)
        report.update(total_items=int(frame.item.nunique()), shown_items=int(counts.sum()), total_intersections=len(intersection_counts(frame)))
    elif kind == "heatmap":
        matrix = matrix_data(frame, "row", "column", "value")
        row_order, column_order = np.arange(len(matrix)), np.arange(len(matrix.columns))
        method, metric = options.get("linkage", "average"), options.get("distance", "euclidean")
        if method == "ward" and metric != "euclidean":
            raise ValueError("Ward linkage requires Euclidean distance")
        if options.get("cluster_rows", True) and len(matrix) > 1:
            row_order = leaves_list(linkage(matrix, method=method, metric=metric))
        if options.get("cluster_columns", True) and len(matrix.columns) > 1:
            column_order = leaves_list(linkage(matrix.T, method=method, metric=metric))
        matrix = matrix.iloc[row_order, column_order]
        center = options.get("center")
        norm = None
        if center is not None:
            span = np.abs(matrix.to_numpy()-center).max()
            if span == 0:
                raise ValueError("Centered heatmap needs a nonzero value range")
            norm = TwoSlopeNorm(vmin=center-span, vcenter=center, vmax=center+span)
        image = ax.imshow(matrix, cmap="RdBu_r" if center is not None else "viridis", norm=norm, aspect="auto")
        ax.set(xticks=range(len(matrix.columns)), xticklabels=matrix.columns, yticks=range(len(matrix)), yticklabels=matrix.index)
        ax.tick_params(labelsize=6); plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        ax.grid(False); ax.figure.colorbar(image, ax=ax, shrink=0.7, label="Value")
        annotation_levels = sorted({str(v) for field in ("row_group", "column_group") if field in frame for v in frame[field].dropna()})
        annotation_colors = category_colors(annotation_levels, preset) if annotation_levels else {}
        for field, key, ordered, rect in [("row_group", "row", matrix.index, [-0.12, 0, 0.035, 1]),
                                           ("column_group", "column", matrix.columns, [0, 1.01, 1, 0.035])]:
            if field in frame:
                require_columns(frame, [field])
                annotation = frame[[key, field]].drop_duplicates()
                require_unique(annotation, [key])
                mapping = dict(zip(annotation[key], annotation[field].astype(str)))
                palette = annotation_colors
                from matplotlib.colors import to_rgba
                values = np.array([to_rgba(palette[mapping[v]]) for v in ordered])
                strip = ax.inset_axes(rect)
                strip.imshow(values[:, None, :] if key == "row" else values[None, :, :], aspect="auto")
                strip.set_axis_off()
                report[field] = {"colors": palette, "mapping": {str(k): v for k, v in mapping.items()}}
        if annotation_colors:
            from matplotlib.patches import Patch
            ax.legend(handles=[Patch(facecolor=color,label=level) for level,color in annotation_colors.items()],
                      title="Annotation group",loc="upper center",bbox_to_anchor=(0.5,-0.20),ncol=min(len(annotation_colors),4),
                      frameon=False,fontsize=6,title_fontsize=7)
        report.update(row_order=list(map(str, matrix.index)), column_order=list(map(str, matrix.columns)), linkage=method, distance=metric, center=center)
    elif kind in {"roc", "pr", "calibration"}:
        report["models"] = {}
        prevalences = []
        for i, model in enumerate(levels):
            data = frame.loc[frame.model == model]
            if data.empty:
                continue
            model_metrics = classification_metrics(data)
            report["models"][model] = model_metrics
            if "sample" in data:
                require_unique(data, ["sample"])
            if kind == "roc":
                x, y, _ = metrics.roc_curve(data.truth, data.score)
                label = f"{model} AUC={model_metrics['auroc']:.3f}"
            elif kind == "pr":
                y, x, _ = metrics.precision_recall_curve(data.truth, data.score)
                label = f"{model} AP={model_metrics['average_precision']:.3f}"
                prevalence = model_metrics["prevalence"]
                if prevalence not in prevalences:
                    ax.axhline(prevalence, color=colors[model], alpha=0.35, linestyle=":", linewidth=0.7)
                    prevalences.append(prevalence)
            else:
                y, x = calibration_curve(data.truth, data.score, n_bins=options.get("bins", 10), strategy="uniform")
                label = f"{model} Brier={model_metrics['brier']:.3f}"
            ax.plot(x, y, color=colors[model], linestyle=LINES[i%4], label=label)
        if kind != "pr":
            ax.plot([0, 1], [0, 1], "--", color="gray", linewidth=0.7)
        labels = {"roc": ("False positive rate", "True positive rate"), "pr": ("Recall", "Precision"), "calibration": ("Mean predicted probability", "Observed positive fraction")}
        ax.set(xlabel=labels[kind][0], ylabel=labels[kind][1], xlim=(0, 1), ylim=(0, 1.03))
        ax.legend(frameon=False, fontsize=6)
    elif kind == "confusion":
        labels = options.get("class_levels", sorted(set(frame.truth.astype(str)) | set(frame.prediction.astype(str))))
        if not (set(frame.truth.astype(str)) | set(frame.prediction.astype(str))) <= set(labels):
            raise ValueError("class_levels must include all observed classes")
        counts = metrics.confusion_matrix(frame.truth.astype(str), frame.prediction.astype(str), labels=labels)
        image = ax.imshow(counts, cmap="Blues")
        for y, x in np.ndindex(counts.shape):
            ax.text(x, y, str(counts[y, x]), ha="center", va="center", color="white" if counts[y, x] > counts.max()/2 else "black", fontsize=7)
        ax.set(xticks=range(len(labels)), xticklabels=labels, yticks=range(len(labels)), yticklabels=labels, xlabel="Predicted", ylabel="Observed")
        ax.grid(False)
        report.update(labels=labels, counts=counts.tolist(), accuracy=float(np.trace(counts)/counts.sum()))
    elif kind == "prediction":
        report["models"] = {}
        for i, model in enumerate(levels):
            data = frame.loc[frame.model == model]
            if data.empty:
                continue
            ax.scatter(data.observed, data.predicted, s=12, color=colors[model], marker=MARKERS[i], alpha=0.7, label=model)
            report["models"][model] = {"n": len(data), "rmse": float(np.sqrt(metrics.mean_squared_error(data.observed, data.predicted))),
                                        "mae": float(metrics.mean_absolute_error(data.observed, data.predicted)),
                                        "r2": float(metrics.r2_score(data.observed, data.predicted)) if len(data)>1 and data.observed.var()>0 else None}
        low, high = frame[["observed", "predicted"]].min().min(), frame[["observed", "predicted"]].max().max()
        ax.plot([low, high], [low, high], "--", color="gray", linewidth=0.7)
        ax.set(xlabel="Observed", ylabel="Predicted"); ax.legend(frameon=False, fontsize=6)
    elif kind == "ablation":
        require_unique(frame, ["model", "component"])
        components = list(dict.fromkeys(frame.component.astype(str)))
        for i, model in enumerate(levels):
            data = frame.loc[frame.model == model].set_index("component").reindex(components)
            ax.scatter(data.value, np.arange(len(components))+i*0.12, color=colors[model], marker=MARKERS[i], label=model, s=18)
        ax.set(yticks=np.arange(len(components))+(len(levels)-1)*0.06, yticklabels=components, xlabel=options.get("value_label", "Score"))
        ax.legend(frameon=False, fontsize=6)
    elif kind == "network":
        require_unique(frame, ["source", "target"])
        directed = options.get("directed", False)
        graph = nx.DiGraph() if directed else nx.Graph()
        if "weight" in frame:
            require_columns(frame, ["weight"], ["weight"])
        for row in frame.itertuples():
            graph.add_edge(str(row.source), str(row.target), weight=getattr(row, "weight", 1))
        if not directed and len(graph.edges) != len(frame):
            raise ValueError("Undirected reciprocal edges are duplicates; resolve explicitly")
        layout = options.get("layout", "spring")
        if layout not in {"spring", "circular"}:
            raise ValueError("network layout must be spring or circular")
        # Layout uses topology; signed biological weights are not treated as distances.
        positions = nx.spring_layout(graph, seed=options.get("seed", 2026), weight=None) if layout == "spring" else nx.circular_layout(graph)
        nx.draw_networkx(graph, positions, ax=ax, node_color="#56B4E9", node_size=170, font_size=6,
                         font_color=ax.xaxis.label.get_color(), edge_color="gray", arrows=directed, width=0.8)
        ax.set_axis_off()
        report.update(nodes=len(graph.nodes), edges=len(graph.edges), layout=layout, directed=directed, layout_uses_weights=False)
    elif kind == "umap":
        require_unique(frame, ["cell"])
        for i, group in enumerate(levels):
            data = frame.loc[frame.group == group]
            ax.scatter(data.umap1, data.umap2, s=9, color=colors[group], marker=MARKERS[i], label=group, alpha=0.8)
        ax.set(xlabel="UMAP 1", ylabel="UMAP 2"); ax.legend(frameon=False, fontsize=6)
        report["embedding"] = "supplied coordinates; no embedding computed"
    elif kind == "dotplot":
        require_unique(frame, ["group", "gene"])
        _probability(frame.fraction, "fraction")
        genes = list(dict.fromkeys(frame.gene.astype(str)))
        image = ax.scatter(frame.gene.astype(str).map({g:i for i,g in enumerate(genes)}), frame.group.map({g:i for i,g in enumerate(levels)}),
                           s=frame.fraction*160, c=frame.mean_expression, cmap="viridis", edgecolors="gray", linewidth=0.3)
        ax.set(xticks=range(len(genes)), xticklabels=genes, yticks=range(len(levels)), yticklabels=levels)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        ax.figure.colorbar(image, ax=ax, label="Mean expression", shrink=0.7)
        handles = [ax.scatter([], [], s=f*160, color="gray", label=f"{f:.0%}") for f in (0.25, 0.5, 1)]
        ax.legend(handles=handles, title="Expressing", frameon=False, fontsize=6, title_fontsize=7)
    if options.get("title"):
        ax.set_title(options["title"])
    for name in ("xlabel", "ylabel", "xlim", "ylim"):
        if name in options:
            getattr(ax, f"set_{name}")(options[name])
    if "inset" in options:
        if kind not in {"ribbon", "prediction", "umap"}:
            raise ValueError("Zoom inset supports ribbon, prediction and umap recipes")
        inset = options["inset"]
        child = ax.inset_axes(inset.get("bounds", [0.55, 0.12, 0.4, 0.4]))
        child_options = {k:v for k,v in options.items() if k not in {"inset", "title", "xlim", "ylim"}}
        draw_recipe(kind, frame, child, preset=preset, options=child_options)
        if child.get_legend():
            child.get_legend().remove()
        child.set(xlim=inset["xlim"], ylim=inset["ylim"], xlabel="", ylabel="")
        child.tick_params(labelsize=6)
        child.xaxis.set_major_locator(MaxNLocator(3))
        child.yaxis.set_major_locator(MaxNLocator(3))
        ax.indicate_inset_zoom(child, edgecolor="gray")
    return report
