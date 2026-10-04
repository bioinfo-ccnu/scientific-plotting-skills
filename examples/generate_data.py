"""Generate shared, explicitly synthetic style demonstration data."""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 2026
rng = np.random.default_rng(SEED)
out = Path(__file__).resolve().parent / "data"
out.mkdir(exist_ok=True)
groups = ["Model A", "Model B", "Model C"]
rows, distribution, scatter = [], [], []
for i, group in enumerate(groups):
    for x in np.linspace(0, 12, 13):
        rows.append((group, x, (1 - np.exp(-x / (2.5 + i))) * (0.65 + i * 0.13)))
    for value in rng.normal(0.45 + i * 0.18, 0.10, 24):
        distribution.append((group, value))
    for x in rng.uniform(0.05, 1, 20):
        scatter.append((group, x, 0.6 * x + 0.10 * i + rng.normal(0, 0.07)))
pd.DataFrame(rows, columns=["group", "x", "response"]).to_csv(out / "curves.csv", index=False)
pd.DataFrame(distribution, columns=["group", "value"]).to_csv(out / "distributions.csv", index=False)
pd.DataFrame(scatter, columns=["group", "x", "y"]).to_csv(out / "scatter.csv", index=False)
pd.DataFrame([(f"Feature {r+1}", f"Sample {c+1}", rng.normal()) for r in range(4) for c in range(5)],
             columns=["feature", "sample", "value"]).to_csv(out / "matrix.csv", index=False)
