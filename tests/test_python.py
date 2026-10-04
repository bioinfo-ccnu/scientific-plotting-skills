import json
from pathlib import Path
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/scientific-plotting/scripts"))
from scientific_style import CONFIG, category_colors, export_figure, figure_style, palette


@pytest.mark.parametrize("preset", CONFIG["presets"])
def test_preset_renders_and_restores_settings(preset, tmp_path):
    previous = matplotlib.rcParams.copy()
    with figure_style(preset):
        fig, ax = plt.subplots(layout="constrained")
        ax.plot([0, 1, 2], [0, 1, 0], label="Observed")
        ax.set(xlabel="Time (h)", ylabel="Response (a.u.)")
        ax.legend()
        export_figure(fig, tmp_path / preset, formats=("png",), dpi=100)
        plt.close(fig)
    assert dict(matplotlib.rcParams) == dict(previous)
    assert (tmp_path / f"{preset}.png").stat().st_size > 1000


def test_rc_restored_on_error():
    previous = matplotlib.rcParams.copy()
    with pytest.raises(RuntimeError), figure_style("dark"):
        raise RuntimeError("Simulated plot failure")
    assert dict(matplotlib.rcParams) == dict(previous)


def test_exports_exact_dimensions_editable_svg_and_provenance(tmp_path):
    with figure_style("nature"):
        fig, ax = plt.subplots(layout="constrained")
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("Time (h)")
        original = tuple(fig.get_size_inches())
        paths = export_figure(fig, tmp_path / "figure.v1", formats=("pdf", "svg", "png", "tiff"),
                              width_mm=100, height_mm=70, dpi=300,
                              metadata={"source": "test", "synthetic": True})
        assert tuple(fig.get_size_inches()) == original
        plt.close(fig)
    for fmt in ("png", "tiff"):
        with Image.open(paths[fmt]) as image:
            assert abs(image.width - 100 / 25.4 * 300) <= 1
            assert abs(image.height - 70 / 25.4 * 300) <= 1
    pdf = paths["pdf"].read_bytes()
    assert pdf.startswith(b"%PDF")
    bounds = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
    assert bounds is not None
    assert float(bounds[1]) == pytest.approx(100 / 25.4 * 72)
    assert float(bounds[2]) == pytest.approx(70 / 25.4 * 72)
    assert "<text" in paths["svg"].read_text()
    record = json.loads(paths["manifest"].read_text())
    assert record["metadata"]["synthetic"] is True
    assert record["width_mm"] == 100


def test_preflight_preserves_existing_files_and_rejects_invalid_values(tmp_path):
    fig, _ = plt.subplots()
    stem = tmp_path / "existing"
    existing = tmp_path / "existing.png"
    existing.write_bytes(b"keep me")
    with pytest.raises(FileExistsError):
        export_figure(fig, stem)
    assert existing.read_bytes() == b"keep me"
    assert not (tmp_path / "existing.pdf").exists()
    for kwargs in ({"formats": ("png", "jpeg")}, {"dpi": 0}, {"width_mm": float("nan")},
                   {"formats": "png"}, {"metadata": {"bad": float("nan")}}):
        with pytest.raises(ValueError):
            export_figure(fig, tmp_path / "invalid", **kwargs)
    assert not list(tmp_path.glob("invalid*"))
    plt.close(fig)


def test_render_failure_leaves_no_published_outputs(tmp_path, monkeypatch):
    fig, _ = plt.subplots()
    original = fig.savefig
    def fail_svg(path, **kwargs):
        if kwargs["format"] == "svg":
            raise RuntimeError("Simulated device error")
        return original(path, **kwargs)
    monkeypatch.setattr(fig, "savefig", fail_svg)
    with pytest.raises(RuntimeError):
        export_figure(fig, tmp_path / "failed")
    assert not list(tmp_path.iterdir())
    plt.close(fig)


def test_semantic_colors_and_capacity():
    mapping = category_colors(["Control", "Treatment"])
    assert mapping == {"Control": "#0072B2", "Treatment": "#D55E00"}
    with pytest.raises(ValueError):
        category_colors(["Control", "Control"])
    for n in (0, 9, True, 2.5):
        with pytest.raises(ValueError):
            palette(n)
