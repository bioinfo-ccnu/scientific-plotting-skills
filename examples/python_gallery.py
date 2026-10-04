"""Run from any working directory; all inputs are synthetic (seed 2026)."""
import argparse
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/scientific-plotting/scripts"))
from scientific_style import CONFIG, category_colors, export_figure, figure_style


def draw(preset, out, overwrite=False):
    data_dir = ROOT / "examples/data"
    curves, distributions, scatter, matrix = [pd.read_csv(data_dir / f"{name}.csv") for name in
                                              ("curves", "distributions", "scatter", "matrix")]
    groups = ["Model A", "Model B", "Model C"]
    colors = category_colors(groups, preset)
    width, height = {"presentation": (260, 200), "poster": (350, 270)}.get(preset, (180, 140))
    with figure_style(preset, overrides={"figure.figsize": (width/25.4, height/25.4)}):
        fig, axes = plt.subplots(2, 2, layout="constrained")
        for i, group in enumerate(groups):
            curve = curves.loc[curves.group == group]
            sample = distributions.loc[distributions.group == group, "value"].to_numpy()
            points = scatter.loc[scatter.group == group]
            axes[0, 0].plot(curve.x, curve.response, color=colors[group], label=group,
                            marker=["o", "s", "^"][i], linestyle=["-", "--", "-."][i], markersize=3)
            box = axes[0, 1].boxplot([sample], positions=[i+1], widths=0.5, patch_artist=True,
                                    showfliers=False, medianprops={"color": colors[group]})
            for patch in box["boxes"]:
                patch.set(facecolor=colors[group], alpha=0.25, edgecolor=colors[group])
            jitter = np.random.default_rng(2026+i).uniform(-0.14, 0.14, len(sample))
            axes[0, 1].scatter(i+1+jitter, sample, color=colors[group], marker=["o", "s", "^"][i], s=12, alpha=0.75)
            axes[1, 0].scatter(points.x, points.y, color=colors[group], marker=["o", "s", "^"][i], s=15, alpha=0.8)
        axes[0, 0].set(xlabel="Time (h)", ylabel="Response (a.u.)", title="A  Response curves")
        axes[0, 0].legend(frameon=False, loc="lower right")
        axes[0, 1].set(xticks=[1, 2, 3], xticklabels=groups, ylabel="Score (a.u.)", title="B  Distributions")
        axes[1, 0].set(xlabel="Input (a.u.)", ylabel="Output (a.u.)", title="C  Association")
        values = matrix.pivot(index="feature", columns="sample", values="value")
        limit = float(np.abs(values.to_numpy()).max())
        axes[1, 1].grid(False)
        image = axes[1, 1].imshow(values, cmap="Greys" if preset == "ieee" else "RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
        axes[1, 1].set(xticks=range(5), xticklabels=["S1", "S2", "S3", "S4", "S5"],
                       yticks=range(4), yticklabels=["F1", "F2", "F3", "F4"], title="D  Signed matrix")
        fig.colorbar(image, ax=axes[1, 1], label="Value (a.u.)", shrink=0.85)
        fig.suptitle(f"{preset.upper()} · Python | SYNTHETIC DATA", fontsize=CONFIG["presets"][preset]["font_size"]+1)
        export_figure(fig, out / f"python-{preset}", formats=("pdf", "svg", "png"), width_mm=width,
                      height_mm=height, dpi=180, overwrite=overwrite,
                      metadata={"preset": preset, "synthetic": True, "seed": 2026, "source": "examples/data/*.csv"})
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "build/python")
    parser.add_argument("--preset", choices=["all", *CONFIG["presets"]], default="all")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for preset in CONFIG["presets"] if args.preset == "all" else [args.preset]:
        draw(preset, args.out, args.overwrite)
