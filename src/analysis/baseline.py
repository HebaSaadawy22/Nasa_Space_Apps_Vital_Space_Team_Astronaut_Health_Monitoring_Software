"""Personal baseline: compare today's values with the astronaut's own early readings."""
from __future__ import annotations

import pandas as pd

from src.utils.constants import FIELDS, ORDER


def compute_baseline(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Mean and standard deviation of the first `window` days for each field."""
    base = df.sort_values("day").head(window)
    rows = []
    for k in ORDER:
        rows.append({"field": k, "mean": base[k].mean(), "std": base[k].std(ddof=0)})
    return pd.DataFrame(rows).set_index("field")


def deviations(df: pd.DataFrame, window: int = 5, z_flag: float = 2.0) -> pd.DataFrame:
    """Latest value vs baseline. A small floor on std keeps flat baselines from exploding."""
    if len(df) <= window:
        raise ValueError("Need more days than the baseline window.")
    base = compute_baseline(df, window)
    latest = df.sort_values("day").iloc[-1]
    rows = []
    for k in ORDER:
        floor = max(base.loc[k, "std"], 0.03 * abs(base.loc[k, "mean"]), 1e-6)
        z = (float(latest[k]) - base.loc[k, "mean"]) / floor
        rows.append({
            "field": k,
            "label": FIELDS[k]["label"],
            "baseline": round(base.loc[k, "mean"], FIELDS[k]["dec"] + 1),
            "latest": float(latest[k]),
            "change": round(float(latest[k]) - base.loc[k, "mean"], FIELDS[k]["dec"] + 1),
            "z": round(z, 2),
            "flag": abs(z) >= z_flag,
        })
    return pd.DataFrame(rows)
