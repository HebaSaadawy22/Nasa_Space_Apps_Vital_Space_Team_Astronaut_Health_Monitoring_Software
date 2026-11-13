"""Trend and hazard risk scoring from a readings DataFrame."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.health_engine import indicator_level
from src.utils.constants import FIELDS, HAZARDS, INDICATOR_BY_ID, INDICATORS


def slope(series: pd.Series, days: int = 7) -> float:
    """Least-squares slope per day over the last `days` values."""
    y = series.tail(days).to_numpy(dtype=float)
    if len(y) < 3:
        return 0.0
    x = np.arange(len(y))
    return float(np.polyfit(x, y, 1)[0])


def trend_report(df: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    """Direction and days until the first field leaves its normal range, if the trend continues."""
    df = df.sort_values("day")
    rows = []
    for ind in INDICATORS:
        k = ind["fields"][0]
        s = slope(df[k], days)
        cur = float(df[k].iloc[-1])
        lo, hi = FIELDS[k]["ok"]
        span = max(hi - lo, 1e-9)
        rel = s / span
        direction = "stable" if abs(rel) < 0.01 else ("rising" if s > 0 else "falling")
        days_left = None
        if lo <= cur <= hi and abs(s) > 1e-9:
            edge = hi if s > 0 else lo
            days_left = int(np.ceil((edge - cur) / s))
        rows.append({"indicator": ind["id"], "name": ind["name"], "slope_per_day": round(s, 3),
                     "direction": direction, "days_to_leave_range": days_left})
    return pd.DataFrame(rows)


def hazard_scores(df: pd.DataFrame) -> pd.DataFrame:
    """0 to 100 score per hazard. Current level counts 70 percent, adverse trend 30 percent."""
    df = df.sort_values("day")
    latest = df.iloc[-1]
    trends = trend_report(df).set_index("indicator")
    rows = []
    for h in HAZARDS:
        lv = [indicator_level(i, latest) for i in h["indicators"]]
        level_part = np.mean(lv) / 2
        adverse = []
        for i in h["indicators"]:
            k = INDICATOR_BY_ID[i]["fields"][0]
            lo, hi = FIELDS[k]["ok"]
            mid = (lo + hi) / 2
            s = trends.loc[i, "slope_per_day"]
            moving_out = (float(latest[k]) >= mid and s > 0) or (float(latest[k]) < mid and s < 0)
            adverse.append(1.0 if moving_out and trends.loc[i, "direction"] != "stable" else 0.0)
        score = round(100 * (0.7 * level_part + 0.3 * float(np.mean(adverse))))
        rows.append({"hazard": h["id"], "name": h["name"], "score": int(score)})
    return pd.DataFrame(rows)
