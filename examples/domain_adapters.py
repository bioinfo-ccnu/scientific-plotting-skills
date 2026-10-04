"""Display supplied synthetic coordinates through Scanpy; no embedding inference."""
from pathlib import Path
import sys
import argparse
import numpy as np
import pandas as pd
import anndata as ad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/scientific-plotting/scripts"))
from specialized_adapters import scanpy_umap
from scientific_style import figure_style, category_colors, export_figure

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "build/domain-python")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    frame = pd.read_csv(ROOT / "skills/scientific-plotting/assets/templates/umap.csv")
    obs = pd.DataFrame({"group": pd.Categorical(frame.group)}, index=frame.cell.astype(str))
    data = ad.AnnData(np.zeros((len(obs), 1)), obs=obs)
    data.obsm["X_umap"] = frame[["umap1", "umap2"]].to_numpy()
    with figure_style("nature"):
        fig, ax = plt.subplots()
        scanpy_umap(data, color="group", ax=ax, palette=category_colors(list(obs.group.cat.categories), "nature"),
                    title="SYNTHETIC DATA | supplied coordinates")
        export_figure(fig, args.out / "scanpy-umap", width_mm=160, height_mm=120,
                      metadata={"synthetic": True, "embedding": "supplied template coordinates"}, overwrite=args.overwrite)
        plt.close(fig)
