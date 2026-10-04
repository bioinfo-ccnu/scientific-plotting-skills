# Optional domain adapters

The 22 core recipes work without these libraries. Use adapters when their specialized features are helpful; install in the selected project's environment. They render supplied analysis results and do not perform differential expression, enrichment, single-cell preprocessing or embedding inference.

## R: ComplexHeatmap and ggraph

```r
install.packages(c("ggraph", "igraph", "BiocManager"))
BiocManager::install("ComplexHeatmap", ask = FALSE, update = FALSE)
source("/path/to/skill/scripts/plot_cli.R")
source("/path/to/skill/scripts/specialized_adapters.R")
edges <- load_scientific_table("edges.csv")
network <- ggraph_scientific_network(edges, preset="nature", layout="fr", seed=2026)
export_scientific(network, "figures/network", width_mm=160, height_mm=120)

values <- load_scientific_table("heatmap.csv")
heatmap <- complex_scientific_heatmap(values, preset="nature", center=0,
                                    linkage="average", distance="euclidean")
export_scientific(heatmap, "figures/heatmap", width_mm=160, height_mm=120)
```

ComplexHeatmap consumes complete `row,column,value` long data with optional `row_group,column_group` annotations. It returns a grid grob; use grid-aware export, not ggplot additions. Row/column clustering can be disabled independently; Ward requires Euclidean distance. Use the core ggplot recipe or customize ComplexHeatmap directly for additional theme behavior; a preset controls selected typography/colors, not every ComplexHeatmap setting.

The ggraph adapter consumes `source,target` edge rows, with no duplicate undirected pairs. It accepts ggraph layouts and a seed, optional directed arrows and node labels. Edge weights do not alter the supplied topology. The core R network recipe uses a circular layout; Python supports spring/circular layouts. Layouts need not match across libraries. These adapters are functions, not YAML `type` values.

See [ComplexHeatmap's reference book](https://jokergoo.github.io/ComplexHeatmap-reference/book/) and [ggraph's official reference](https://ggraph.data-imaginist.com/reference/ggraph.html) for custom annotation, legend and graph layouts.

## Python: existing AnnData/Scanpy embeddings

```bash
python -m pip install 'scanpy>=1.10,<2'
```

```python
from specialized_adapters import scanpy_umap
from scientific_style import figure_style, export_figure
import matplotlib.pyplot as plt

with figure_style("nature"):
    fig, ax = plt.subplots()
    scanpy_umap("analysis.h5ad", color="cell_type", ax=ax)
    export_figure(fig, "figures/cell-types", width_mm=160, height_mm=120)
```

`scanpy_umap` accepts an AnnData object or `.h5ad` path and requires existing `obsm['X_umap']`. `color` must identify an observation field or gene. Supply a palette for categorical consistency. It never computes embeddings or silently reruns analysis. For CSV coordinates use the core `umap` recipe; for supplied expression summaries use `dotplot`. Describe normalization and what the expression fraction counts in the caption. Refer to [Scanpy's plotting API](https://scanpy.readthedocs.io/en/stable/api/plotting.html) for richer AnnData plotting.

Install the core Python recipe dependencies from [configuration.md](configuration.md) as needed. In a repository checkout, `requirements-single-cell.txt` includes the core requirements and Scanpy.
