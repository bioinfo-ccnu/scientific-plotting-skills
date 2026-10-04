# Figure review and export

Review a rendered PNG at the intended physical size, not only a zoomed editor view. Confirm all panels have readable labels, units and ticks; no clipped titles/legends; visible markers and intervals; consistent category colors; distinguishable grayscale encodings when required; and an explanation of sample size and uncertainty where applicable.

Use explicit margins or a layout engine. Avoid `bbox_inches="tight"` for exact-width exports: it changes the final canvas size. The helpers use requested dimensions and render all formats before moving files out of staging. R's standard PDF device rounds page bounds to whole points; its manifest includes measured PDF dimensions. They reject existing outputs unless `overwrite` is enabled. Concurrent writers should use separate output stems; publishing several files is not a transactional filesystem operation.

Vector PDF and SVG suit lines/text. Dense scatter/heatmap layers may need selective rasterization while text remains vector. A raster at 300 dpi is often useful for previews; 600 dpi may be useful for line art, but verify the actual requested specification. Do not convert a low-resolution image to a high-DPI wrapper and call it higher quality.

Expected pixel size is approximately `mm / 25.4 * dpi`; raster devices can round or truncate by one pixel. PDF canvas dimensions are points (`mm / 25.4 * 72`). Verify format signatures and dimensions when exports are critical. SVG text stays editable; PDF font behavior depends on the backend/device.

Keep the source script, source-data path/identifier, random seed if any stochastic layout or demonstration is used, selected style, installed versions and output dimensions. Helpers write `*.plot.json` with basic metadata; explicitly pass data provenance, caption definitions and seed where relevant. Metadata records environment facts, not a claim of complete reproducibility without the input data and script.

If input is absent, create only a clearly labeled synthetic example when a demonstration is requested, or ask for the needed data while preparing the plotting workflow. Do not report an illustrative figure as an experimental finding.
