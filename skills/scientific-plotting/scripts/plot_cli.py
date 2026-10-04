"""YAML-driven scientific plotting: python plot_cli.py config.yml."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from plot_data import load_table
from plot_recipes import draw_recipe, CATALOG
from plot_statistics import compare_groups, annotate_comparisons
from scientific_style import figure_style, export_figure, category_colors
from figure_tools import figure_quality, inspect_exports, label_panels, shared_legend


def load_config(path):
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Configuration must be a mapping with version: 1")
    if not isinstance(config.get("panels"), list) or not config["panels"]:
        raise ValueError("Configuration needs at least one panel")
    for panel in config["panels"]:
        if panel.get("type") not in CATALOG or not panel.get("data"):
            raise ValueError("Each panel needs a supported type and data path")
        if panel.get("statistics") and panel["type"] not in {"raincloud", "paired"}:
            raise ValueError("Statistical brackets support raincloud and paired panels")
    return config


def _paths(stem, formats, statistics=False):
    suffixes = [*formats, "plot.json", "qc.json", "config.yml", "source.py"]
    if statistics:
        suffixes += ["statistics.csv"]
    return [Path(str(stem)+"."+suffix) for suffix in suffixes]


def run_config(path, *, backend=None, output=None, overwrite=False):
    config_path = Path(path).resolve()
    config = load_config(config_path)
    backend = backend or config.get("backend", "python")
    if backend == "r":
        script = Path(__file__).with_suffix(".R")
        command = ["Rscript", str(script), str(config_path)]
        if output:
            command += ["--output", str(Path(output).resolve())]
        if overwrite:
            command += ["--overwrite"]
        subprocess.run(command, check=True)
        return []
    if backend != "python":
        raise ValueError("backend must be python or r")
    presets = config.get("presets", [config.get("preset", "science")])
    if not isinstance(presets, list) or not presets or len(set(presets)) != len(presets):
        raise ValueError("presets must be a nonempty unique list")
    formats = config.get("formats", ["pdf", "svg", "png"])
    if not isinstance(formats, list) or not formats or len(set(formats)) != len(formats) or set(formats)-{"pdf", "svg", "png", "tiff"}:
        raise ValueError("formats must be a unique list of supported formats")
    output_base = Path(output).resolve() if output else config_path.parent / config.get("output", "figures/figure")
    has_statistics = any(panel.get("statistics") for panel in config["panels"])
    destinations = [p for preset in presets for p in _paths(Path(str(output_base)+"-"+preset), formats, has_statistics)]
    for destination in destinations:
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Output exists: {destination}; use a fresh stem or --overwrite")
    frames, sources = [], []
    for panel in config["panels"]:
        data_path = (config_path.parent / panel["data"]).resolve()
        frames.append(load_table(data_path, columns=panel.get("columns"), sheet=panel.get("sheet", 0), reshape=panel.get("reshape")))
        sources.append({"path": str(data_path), "sha256": hashlib.sha256(data_path.read_bytes()).hexdigest()})
    width, height, dpi = config.get("width_mm", 180), config.get("height_mm", 120), config.get("dpi", 300)
    if any(not isinstance(v, (int,float)) or isinstance(v,bool) or not 0 < v < float("inf") for v in (width,height,dpi)):
        raise ValueError("Dimensions and DPI must be finite positive numbers")
    layout = config.get("layout", {})
    ncols = layout.get("ncols", min(2,len(frames)))
    if not isinstance(ncols, int) or isinstance(ncols,bool) or ncols < 1:
        raise ValueError("layout.ncols must be a positive integer")
    levels = config.get("category_levels")
    if levels is None:
        levels = []
        for frame in frames:
            column = "model" if "model" in frame else "group" if "group" in frame else None
            if column:
                levels += [v for v in frame[column].dropna().astype(str).unique() if v not in levels]
    output_base.parent.mkdir(parents=True, exist_ok=True)
    results = []
    # Stage the complete style batch. A malformed late preset does not publish a partial batch.
    with tempfile.TemporaryDirectory(prefix=".batch-", dir=output_base.parent) as temporary:
        staged_files = []
        for preset in presets:
            colors = category_colors(levels, preset) if levels else {}
            with figure_style(preset, overrides={"figure.figsize": (width/25.4, height/25.4)}):
                rows = (len(frames)+ncols-1)//ncols
                fig, axes = plt.subplots(rows, ncols, squeeze=False, layout="constrained", sharex=layout.get("sharex",False), sharey=layout.get("sharey",False))
                reports, statistics, annotations = [], [], []
                try:
                    for index, (panel, frame, ax) in enumerate(zip(config["panels"], frames, axes.flat)):
                        options = dict(panel.get("options", {}))
                        if "group" in frame or "model" in frame:
                            column = "model" if "model" in frame else "group"
                            local_levels = [level for level in levels if level in set(frame[column].astype(str))]
                            options.update(levels=local_levels, colors=colors)
                        reports.append(draw_recipe(panel["type"], frame, ax, preset=preset, options=options))
                        if panel.get("statistics"):
                            table = compare_groups(frame, **panel["statistics"])
                            annotations.append((ax, table, local_levels))
                            table.insert(0, "panel", index+1)
                            statistics.append(table)
                    # Finish all data limits before annotations lock shared axes.
                    for ax, table, local_levels in annotations:
                        annotate_comparisons(ax, table, local_levels)
                    active = list(axes.flat)[:len(frames)]
                    for ax in list(axes.flat)[len(frames):]:
                        ax.remove()
                    if layout.get("tags", True):
                        label_panels(active, layout.get("labels"))
                    if layout.get("shared_legend", False):
                        shared_legend(fig, active)
                    if config.get("title"):
                        fig.suptitle(config["title"])
                    report = figure_quality(fig, **config.get("quality", {}))
                    stage_stem = Path(temporary) / (output_base.name+"-"+preset)
                    metadata = {"preset": preset, "synthetic": config.get("synthetic",False), "sources": sources,
                                "category_colors": colors, "recipes": reports, "statistics": [t.to_dict(orient="records") for t in statistics],
                                "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest()}
                    paths = export_figure(fig, stage_stem, formats=formats, width_mm=width, height_mm=height, dpi=dpi, metadata=metadata)
                    report["exports"] = inspect_exports(paths, width_mm=width, height_mm=height, dpi=dpi)
                    if report["exports"]["findings"]:
                        report["status"] = "review"
                    Path(str(stage_stem)+".qc.json").write_text(json.dumps(report,indent=2)+"\n")
                    # Normalize paths for a rerunnable delivered configuration.
                    delivered_config = dict(config)
                    delivered_config["backend"] = "python"
                    delivered_config["output"] = str(output_base)
                    delivered_config["panels"] = [dict(p, data=s["path"]) for p,s in zip(config["panels"],sources)]
                    Path(str(stage_stem)+".config.yml").write_text(yaml.safe_dump(delivered_config,sort_keys=False))
                    source = "# Reproduce using the installed scientific-plotting skill\nfrom pathlib import Path\nimport sys\nif len(sys.argv) != 2:\n    raise SystemExit('Usage: python SOURCE.py /path/to/skill/scripts')\nsys.path.insert(0, sys.argv[1])\nfrom plot_cli import run_config\nrun_config(Path(__file__).with_suffix('.yml').with_name(Path(__file__).name.replace('.source.py','.config.yml')), overwrite=True)\n"
                    Path(str(stage_stem)+".source.py").write_text(source)
                    if statistics:
                        import pandas as pd
                        pd.concat(statistics,ignore_index=True).to_csv(str(stage_stem)+".statistics.csv",index=False)
                    final_stem = Path(str(output_base)+"-"+preset)
                    staged_files += list(zip(_paths(stage_stem,formats,has_statistics), _paths(final_stem,formats,has_statistics)))
                    results.append({"stem": str(final_stem), "quality": report["status"], "metrics": reports})
                finally:
                    plt.close(fig)
        for source, destination in staged_files:
            if destination.exists() and not overwrite:
                raise FileExistsError(f"Output appeared during batch: {destination}")
            source.replace(destination)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--backend", choices=["python","r"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for result in run_config(args.config, backend=args.backend, output=args.output, overwrite=args.overwrite):
        print(json.dumps(result))
