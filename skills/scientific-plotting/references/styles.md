# Style selection

Both backends read `assets/style-presets.json`. Python applies SciencePlots where listed; R implements original ggplot2 themes with analogous typography and backgrounds. R does not execute SciencePlots.

| Preset | Intended use | Default canvas (mm) | Typography |
|---|---|---:|---|
| `science` | General paper figures | 89 × 64 | Serif, 9 pt |
| `nature` | Compact sans-serif paper figures | 89 × 64 | Sans, 8 pt |
| `ieee` | Compact grayscale engineering figures | 88.9 × 63.5 | Serif, 8 pt |
| `minimal` | Light grid and restrained styling | 110 × 75 | Sans, 9 pt |
| `presentation` | Slides and larger labels | 180 × 110 | Sans, 14 pt |
| `dark` | Dark-background slides | 160 × 100 | Sans, 11 pt |
| `poster` | Large-format communication | 240 × 160 | Sans, 18 pt |
| `accessible` | Color plus marker/line encodings | 120 × 80 | Sans, 10 pt |

These sizes are configurable single-panel defaults, not journal requirements. Scale multi-panel canvases deliberately; scaling a saved image later also scales its text.

Use the Okabe–Ito palette for up to eight categorical levels. The grayscale palette supports four; line types and markers must also identify groups. The accessible preset supplies distinct cycles/scales for line plots, but the author must map shape/line aesthetics and assess contrast for the actual data. Yellow on white can be faint: add a dark outline or choose another available color for thin lines. No preset guarantees accessibility for every figure.

Reuse an explicit global category mapping across subsets. For continuous values, use a perceptually ordered map such as viridis. For signed deviations, use a diverging map centered on a scientifically justified reference, not the sample median by default. Avoid a rainbow map for quantitative heatmaps.

User-specified fonts, colors and layout can override presets. Python takes Matplotlib rc overrides; R themes combine with `theme(...)`. For another named journal style, first verify its current requirements. Do not claim journal endorsement.

Optional extensions: [SciencePlots gallery](https://github.com/garrettj403/SciencePlots/wiki/Gallery), [ggthemes](https://jrnold.github.io/ggthemes/), [ggsci](https://nanx.me/ggsci/). Install only when useful; keep third-party code as dependencies.
