"""Optional Scanpy adapter: displays an existing embedding, never computes it."""
from pathlib import Path


def scanpy_umap(adata_or_path, *, color, ax=None, palette=None, **kwargs):
    try:
        import scanpy as sc
    except ImportError as exc:
        raise ImportError("Install requirements-single-cell.txt for the Scanpy adapter") from exc
    adata = sc.read_h5ad(adata_or_path) if isinstance(adata_or_path,(str,Path)) else adata_or_path
    if "X_umap" not in adata.obsm:
        raise ValueError("AnnData must already contain obsm['X_umap']; this adapter does not compute embeddings")
    if color not in adata.obs and color not in adata.var_names:
        raise ValueError("color must identify an observation field or gene")
    return sc.pl.umap(adata,color=color,ax=ax,palette=palette,show=False,**kwargs)
