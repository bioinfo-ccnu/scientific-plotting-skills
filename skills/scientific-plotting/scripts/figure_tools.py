"""Figure assembly helpers and conservative, inspectable quality checks."""
from itertools import combinations
from pathlib import Path
import json
import warnings
import numpy as np
from matplotlib import font_manager, ft2font
from matplotlib.colors import to_rgba
from matplotlib.text import Text
from PIL import Image


def contrast_ratio(foreground, background):
    f, b = np.array(to_rgba(foreground)), np.array(to_rgba(background))
    rgb = f[:3]*f[3]+b[:3]*(1-f[3])
    def luminance(values):
        linear = np.where(values <= 0.04045, values/12.92, ((values+0.055)/1.055)**2.4)
        return float(linear @ [0.2126, 0.7152, 0.0722])
    light, dark = sorted([luminance(rgb), luminance(b[:3])], reverse=True)
    return (light+0.05)/(dark+0.05)


def shared_legend(fig, axes):
    handles, labels = [], []
    for ax in axes:
        h, l = ax.get_legend_handles_labels()
        for handle, label in zip(h, l):
            if label and not label.startswith("_") and label not in labels:
                handles.append(handle); labels.append(label)
        if ax.get_legend():
            ax.get_legend().remove()
    if handles:
        return fig.legend(handles, labels, loc="outside lower center", ncol=min(len(labels), 4), frameon=False)


def label_panels(axes, labels=None):
    labels = labels or [chr(65+i) for i in range(len(axes))]
    if len(labels) != len(axes):
        raise ValueError("Panel label count must match axes")
    for ax, label in zip(axes, labels):
        ax.text(-0.04, 1.10, label, transform=ax.transAxes, fontweight="bold", fontsize=10, va="bottom")


def figure_quality(fig, *, minimum_font_size=6, minimum_text_contrast=3):
    """Heuristics flag review needs, never certify publication compliance.

    Uses rendered artist bounds/glyph maps. Intentional overlays and complex
    legends can produce false positives; image-internal text is not inspected.
    """
    findings = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        fig.canvas.draw()
    for warning in captured:
        findings.append({"code": "render-warning", "detail": str(warning.message)})
    renderer = fig.canvas.get_renderer()
    width, height = fig.bbox.width, fig.bbox.height
    texts, fonts = [], {}
    for artist in fig.findobj(match=Text):
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        # Tick labels hidden by shared axes should not count.
        bounds = artist.get_window_extent(renderer)
        if not np.isfinite(bounds.get_points()).all():
            continue
        if bounds.width == 0 or bounds.height == 0:
            continue
        content = artist.get_text()
        if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > width+1 or bounds.y1 > height+1:
            findings.append({"code": "clipped-text", "text": content})
        if artist.get_fontsize() < minimum_font_size:
            findings.append({"code": "small-text", "text": content, "points": artist.get_fontsize()})
        font = artist.get_fontproperties()
        try:
            path = font_manager.findfont(font, fallback_to_default=False)
            if path not in fonts:
                fonts[path] = ft2font.FT2Font(path).get_charmap()
            missing = sorted({char for char in content if not char.isspace() and ord(char) not in fonts[path]})
            if missing:
                findings.append({"code": "missing-glyph", "text": content, "characters": missing})
        except ValueError:
            findings.append({"code": "missing-font", "text": content, "family": font.get_family()})
        background = artist.axes.get_facecolor() if artist.axes else fig.get_facecolor()
        ratio = contrast_ratio(artist.get_color(), background)
        if ratio < minimum_text_contrast:
            findings.append({"code": "low-text-contrast", "text": content, "ratio": round(ratio, 2)})
        texts.append((artist, bounds))
    for (a, ba), (b, bb) in combinations(texts, 2):
        if not ba.overlaps(bb):
            continue
        overlap = max(0, min(ba.x1, bb.x1)-max(ba.x0, bb.x0))*max(0, min(ba.y1, bb.y1)-max(ba.y0, bb.y0))
        if overlap > min(ba.width*ba.height, bb.width*bb.height)*0.15:
            findings.append({"code": "text-overlap", "texts": [a.get_text(), b.get_text()]})
    # Check explicitly colored lines against their axes, excluding images/maps.
    for ax in fig.axes:
        for line in ax.lines:
            try:
                ratio = contrast_ratio(line.get_color(), ax.get_facecolor())
                if ratio < 1.5 and line.get_alpha() != 0:
                    findings.append({"code": "low-line-contrast", "label": line.get_label(), "ratio": round(ratio, 2)})
            except (ValueError, TypeError):
                pass
    return {"backend": "matplotlib", "status": "review" if findings else "pass",
            "checks": ["render-warnings", "text-bounds", "text-overlap", "font-glyphs", "font-size", "contrast"],
            "limitations": ["Heuristic geometry can flag intentional overlays", "Does not OCR embedded images or certify journal compliance"],
            "findings": findings}


def inspect_exports(paths, *, width_mm, height_mm, dpi, minimum_dpi=300):
    report = {"files": {}, "findings": []}
    if any(f in paths for f in ("png", "tiff")) and dpi < minimum_dpi:
        report["findings"].append({"code": "low-raster-resolution", "dpi": dpi, "suggested_minimum": minimum_dpi})
    for fmt, path in paths.items():
        if fmt == "manifest":
            continue
        path = Path(path)
        details = {"bytes": path.stat().st_size}
        if fmt in {"png", "tiff"}:
            with Image.open(path) as image:
                details.update(pixels=list(image.size), recorded_dpi=image.info.get("dpi"))
                expected = [width_mm/25.4*dpi, height_mm/25.4*dpi]
                if any(abs(a-b)>1 for a,b in zip(image.size, expected)):
                    report["findings"].append({"code": "wrong-raster-dimensions", "file": str(path)})
        elif fmt == "pdf":
            import re
            box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)", path.read_bytes())
            if box:
                actual = [float(box[1])/72*25.4, float(box[2])/72*25.4]
                details["page_mm"] = actual
                if any(abs(a-b)>0.02 for a,b in zip(actual, [width_mm,height_mm])):
                    report["findings"].append({"code": "pdf-page-rounding", "page_mm": actual})
        elif fmt == "svg":
            import xml.etree.ElementTree as ET
            svg = ET.parse(path).getroot()
            details.update(width=svg.attrib.get("width"), height=svg.attrib.get("height"))
        report["files"][fmt] = details
    return report
