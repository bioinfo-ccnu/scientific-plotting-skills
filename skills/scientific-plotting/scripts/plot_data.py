"""Tabular loading, explicit column mapping and reshape helpers."""
from pathlib import Path
import numpy as np
import pandas as pd


def load_table(path, *, columns=None, sheet=0, reshape=None):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    elif path.suffix.lower() in {".tsv", ".txt"}:
        frame = pd.read_csv(path, sep="\t")
    else:
        raise ValueError("Input must be CSV, TSV or XLSX/XLSM")
    if columns:
        missing = set(columns.values()) - set(frame.columns)
        if missing:
            raise ValueError(f"Mapped source columns missing: {sorted(missing)}")
        if len(set(columns.values())) != len(columns):
            raise ValueError("Each source column can map to only one canonical name")
        frame = frame.rename(columns={source: canonical for canonical, source in columns.items()})
        if frame.columns.duplicated().any():
            raise ValueError("Column mapping created duplicate names")
    if reshape:
        frame = reshape_table(frame, **reshape)
    return frame


def reshape_table(frame, *, mode, id_columns=None, value_columns=None,
                  names_to="variable", values_to="value", index=None, columns=None, values=None):
    if mode == "long":
        if not id_columns or not value_columns:
            raise ValueError("Long reshape needs id_columns and value_columns")
        if names_to in id_columns or values_to in id_columns or names_to == values_to:
            raise ValueError("Reshape output names must not collide with ID columns")
        return frame.melt(id_vars=id_columns, value_vars=value_columns, var_name=names_to, value_name=values_to)
    if mode == "wide":
        if not index or not columns or not values:
            raise ValueError("Wide reshape needs index, columns and values")
        return frame.pivot(index=index, columns=columns, values=values).reset_index()
    raise ValueError("reshape.mode must be long or wide")


def require_columns(frame, columns, numeric=()):
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Input has no observations")
    for column in columns:
        if frame[column].isna().any():
            raise ValueError(f"Missing values in {column}; resolve them explicitly before plotting")
    for column in numeric:
        if not pd.api.types.is_numeric_dtype(frame[column]) or not np.isfinite(frame[column].to_numpy()).all():
            raise ValueError(f"{column} must contain finite numbers")


def require_unique(frame, columns):
    if frame.duplicated(list(columns)).any():
        raise ValueError(f"Duplicate observations for key {list(columns)}; aggregate explicitly if justified")
