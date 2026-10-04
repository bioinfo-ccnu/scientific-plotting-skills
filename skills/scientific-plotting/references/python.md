# Python

Use a project virtual environment. Core packages: Matplotlib, SciencePlots, NumPy and pandas. Seaborn is optional for distributions/statistical visualizations. The repository requirements file lists compatible version ranges; export metadata records installed versions.

Load the helper from the actual installed skill directory:

```python
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")  # before pyplot for headless execution only
import matplotlib.pyplot as plt
import pandas as pd

skill_dir = Path("/actual/path/to/scientific-plotting")
sys.path.insert(0, str(skill_dir / "scripts"))
from scientific_style import figure_style, category_colors, export_figure

data = pd.read_csv("measurements.csv")  # columns: group, x, y
levels = list(dict.fromkeys(data["group"]))
colors = category_colors(levels, "nature")
with figure_style("nature"):
    fig, ax = plt.subplots(layout="constrained")
    for group in levels:
        subset = data.loc[data["group"] == group].sort_values("x")
        ax.plot(subset["x"], subset["y"], color=colors[group], label=group)
    ax.set(xlabel="Time (h)", ylabel="Response (a.u.)")
    ax.legend(frameon=False)
    export_figure(fig, "figures/response", width_mm=89, height_mm=64,
                  metadata={"preset": "nature", "source": "measurements.csv"})
    plt.close(fig)
```

Adapt units and plot type to the actual schema. Avoid connecting unordered observations. Use an explicit `formats=("pdf", "svg", "png", "tiff")` when all formats are needed. Export inside the style context so PDF/SVG typography and background settings apply during rendering. Exporting at a size different from creation can affect layout, so create at the intended size or inspect the resized output.

SciencePlots must be imported to register its styles. The helper does this lazily. The portable default uses `no-latex`; MathText still handles common equations. `latex=True` requires an existing usable TeX installation and may require additional TeX packages. Do not install a TeX distribution automatically.

`figure_style(..., overrides={"font.size": 10, "figure.figsize": (7, 4)})` accepts rc settings. Individual axes can override text size independently. Use `category_colors` across panels; direct Seaborn calls should receive a named palette and explicit `hue_order`. For IEEE/accessible lines, pass group-specific markers and line types if manual color assignment or plotting order would break the default cycle.

For CJK labels, resolve an installed font with the required glyphs using Matplotlib's font manager or a supplied font file; preview all glyphs. Do not use deprecated SciencePlots CJK style names. PDF text is embedded as TrueType where possible; SVG text remains editable and depends on fonts available to the viewer.

Official references: [SciencePlots](https://github.com/garrettj403/SciencePlots), [Matplotlib customization](https://matplotlib.org/stable/users/explain/customizing.html).
