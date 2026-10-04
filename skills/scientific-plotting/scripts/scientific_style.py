"""Shared figure styles and physical-size-preserving exports for Matplotlib."""
from contextlib import contextmanager
from cycler import cycler
import importlib.metadata
import json
import math
import platform
from pathlib import Path
import shutil
import tempfile

import matplotlib as mpl
import matplotlib.pyplot as plt

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "assets/style-presets.json").read_text())


def preset_config(name="science"):
    """Return a preset copy; reject typos instead of changing styles silently."""
    if name not in CONFIG["presets"]:
        raise ValueError(f"Unknown preset {name!r}; choose {', '.join(CONFIG['presets'])}")
    return dict(CONFIG["presets"][name])


def palette(n, preset="science", palette_name=None):
    """Return distinct configured categorical colors; never recycle silently."""
    name = palette_name or preset_config(preset)["palette"]
    if name not in CONFIG["palettes"]:
        raise ValueError(f"Unknown palette: {name}")
    colors = CONFIG["palettes"][name]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= len(colors):
        raise ValueError(f"{name} supports 1–{len(colors)} categories; use another encoding for more")
    return colors[:n]


def category_colors(levels, preset="science", palette_name=None):
    """Create a stable category mapping to reuse across all panels."""
    levels = list(levels)
    if len(set(levels)) != len(levels):
        raise ValueError("Category levels must be unique")
    return dict(zip(levels, palette(len(levels), preset, palette_name)))


@contextmanager
def figure_style(preset="science", *, latex=False, overrides=None):
    """Apply styles temporarily and restore rc settings even on exceptions."""
    config = preset_config(preset)
    styles = list(config["styles"])
    if "science" in styles:
        try:
            import scienceplots  # noqa: F401 -- registers styles
        except ImportError as exc:
            raise ImportError("Install SciencePlots in this Python environment") from exc
    if latex and not shutil.which("latex"):
        raise RuntimeError("latex=True requires an existing LaTeX installation; use latex=False otherwise")
    family = "DejaVu Serif" if config["family"] == "serif" else "DejaVu Sans"
    foreground, background = config["foreground"], config["background"]
    colors = CONFIG["palettes"][config["palette"]]
    cycle = cycler(color=colors)
    if preset in {"ieee", "accessible"}:
        cycle += cycler(linestyle=(["-", "--", "-.", ":"] * 2)[:len(colors)])
        cycle += cycler(marker=["o", "s", "^", "D", "v", "P", "X", "*"][:len(colors)])
    params = {
        "font.family": family, "font.size": config["font_size"],
        "axes.labelsize": config["font_size"], "axes.titlesize": config["font_size"],
        "xtick.labelsize": config["font_size"] * 0.9, "ytick.labelsize": config["font_size"] * 0.9,
        "legend.fontsize": config["font_size"] * 0.85,
        "figure.figsize": (config["width_mm"] / 25.4, config["height_mm"] / 25.4),
        "figure.facecolor": background, "axes.facecolor": background,
        "savefig.facecolor": background, "text.color": foreground,
        "axes.labelcolor": foreground, "axes.edgecolor": foreground,
        "xtick.color": foreground, "ytick.color": foreground,
        "axes.grid": config["grid"], "grid.alpha": 0.18,
        "grid.color": foreground, "axes.prop_cycle": cycle,
        "axes.spines.top": False, "axes.spines.right": False,
        "text.usetex": latex, "svg.fonttype": "none", "pdf.fonttype": 42,
        "savefig.bbox": None, "savefig.dpi": 600 if preset == "ieee" else 300,
    }
    if overrides:
        params.update(overrides)
    with plt.style.context(styles), mpl.rc_context(params):
        yield config


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def export_figure(fig, output_stem, *, formats=("pdf", "svg", "png"), dpi=300,
                  width_mm=None, height_mm=None, metadata=None, overwrite=False):
    """Export exact canvas plus JSON provenance. Call inside figure_style.

    Render every format in a staging directory before moving to destinations.
    No tight-bbox resizing: use a layout engine or explicit subplot margins.
    """
    dpi = _positive(dpi, "dpi")
    if isinstance(formats, str):
        raise ValueError("formats must be a sequence, e.g. ('pdf', 'png')")
    formats = tuple(formats)
    if not formats or len(set(formats)) != len(formats) or any(f not in {"pdf", "svg", "png", "tiff"} for f in formats):
        raise ValueError("Use unique formats from pdf, svg, png, tiff")
    old_size = fig.get_size_inches().copy()
    width = _positive(width_mm if width_mm is not None else old_size[0] * 25.4, "width_mm")
    height = _positive(height_mm if height_mm is not None else old_size[1] * 25.4, "height_mm")
    stem = Path(output_stem).expanduser()
    targets = [Path(str(stem) + "." + f) for f in formats]
    manifest = Path(str(stem) + ".plot.json")
    for target in [*targets, manifest]:
        if target.exists() and not overwrite:
            raise FileExistsError(f"Output already exists: {target}; choose a new stem or overwrite=True")
    record = {
        "backend": "matplotlib", "width_mm": width, "height_mm": height, "dpi": dpi,
        "formats": list(formats), "metadata": metadata or {},
        "versions": {name: importlib.metadata.version(name) for name in ("matplotlib", "numpy")},
    }
    record["versions"]["Python"] = platform.python_version()
    try:
        record["versions"]["SciencePlots"] = importlib.metadata.version("SciencePlots")
    except importlib.metadata.PackageNotFoundError:
        pass
    content = json.dumps(record, indent=2, allow_nan=False) + "\n"
    stem.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.set_size_inches(width / 25.4, height / 25.4, forward=False)
        with tempfile.TemporaryDirectory(prefix=".plot-", dir=stem.parent) as stage:
            staged = []
            for fmt, target in zip(formats, targets):
                temporary = Path(stage) / target.name
                kwargs = {"pil_kwargs": {"compression": "tiff_lzw"}} if fmt == "tiff" else {}
                with mpl.rc_context({"savefig.bbox": None}):
                    fig.savefig(temporary, format=fmt, dpi=dpi, bbox_inches=None, **kwargs)
                staged.append((temporary, target))
            temporary_manifest = Path(stage) / manifest.name
            temporary_manifest.write_text(content, encoding="utf-8")
            for temporary, target in [*staged, (temporary_manifest, manifest)]:
                if target.exists() and not overwrite:
                    raise FileExistsError(f"Output appeared during export: {target}")
                temporary.replace(target)
    finally:
        fig.set_size_inches(old_size, forward=False)
    return {fmt: path for fmt, path in zip(formats, targets)} | {"manifest": manifest}
