# Automated quality checks

The YAML runner writes a `*.qc.json` report per style. Python inspects Matplotlib artists after rendering; R inspects rendered SVG text geometry using xml2/systemfonts. Both inspect exports. Missing fonts/glyphs, small text, estimated text overlap/clipping, low text/line contrast, physical dimensions and raster resolution produce findings with review status. Captured rendering warnings are preserved.

These are **heuristics**, not a journal compliance certificate or automatic layout repair. They cannot infer whether statistics are appropriate, whether a caption is truthful, whether every drawn mark overlaps, or how a rasterized external image looks. Rotation, compound panels, insets, legend backgrounds and antialiasing can cause false positives or missed issues. An artist's background estimate may differ from the color behind its actual pixels. R text-box estimates use SVG geometry and font metrics, not OCR or a full SVG layout engine.

`quality` configuration keys: `minimum_font_size` (6 pt) and `minimum_text_contrast` (3). Python also checks line contrast against a fixed threshold of 1.5. Keep appropriate readability thresholds; do not lower them merely to obtain `pass`. A `review` result identifies possible issues, and a `pass` means no issue was detected by these checks. Render and inspect the final-size figure in either case, correct observed problems, and repeat the relevant export.

PNG/TIFF dimensions and resolution, PDF page bounds and SVG dimensions are checked where the backend supports them. Raster exports under 300 dpi are flagged; demonstration galleries intentionally use 180 dpi previews and retain vector exports. R's whole-point PDF rounding can trigger a page-size finding, with the measured discrepancy recorded. Use requested dimensions appropriate for the destination rather than treating these defaults as publication policy.

Direct `scientific_style` export helpers produce the manifest but do not run the full automatic QA runner. In custom code use `figure_tools.py` / `figure_tools.R` explicitly or perform the relevant visual and format checks yourself.
