"""Per-astronaut stateful feature engineering.

Matches the notebook exactly: rolling means use the PREVIOUS 3 readings only
(shift(1).rolling(3)), and a feature is None until 3 previous readings exist.
"""
from __future__ import annotations

from collections import defaultdict, deque

from .config import ML_FEATURES, ROLLING_SOURCES, ROLLING_WINDOW


class FeatureEngine:
    def __init__(self, window: int = ROLLING_WINDOW):
        self.window = window
        # astronaut_id -> column -> last `window` values (excluding the current reading)
        self._history: dict[str, dict[str, deque]] = defaultdict(
            lambda: {c: deque(maxlen=window) for c in ROLLING_SOURCES}
        )
        self._last: dict[str, dict[str, float]] = {}
        self._last_ts: dict[str, str] = {}

    def is_stale(self, astronaut_id: str, timestamp: str) -> bool:
        """True if this reading is not newer than the last one processed (duplicate/out of order)."""
        last = self._last_ts.get(astronaut_id)
        return last is not None and timestamp <= last

    def process(self, r: dict) -> dict:
        """Take a validated, typed reading; return it plus engineered features. Updates state."""
        aid = r["astronaut_id"]
        hist = self._history[aid]
        out = dict(r)

        for col, prefix in ROLLING_SOURCES.items():
            h = hist[col]
            baseline = sum(h) / self.window if len(h) == self.window else None
            out[f"{prefix}_rolling_3d"] = baseline
            out[f"{prefix}_deviation"] = (r[col] - baseline) if baseline is not None else None

        prev = self._last.get(aid)
        out["hr_change"] = (r["heart_rate"] - prev["heart_rate"]) if prev else None
        out["sleep_change"] = (r["sleep_hours"] - prev["sleep_hours"]) if prev else None

        # update state AFTER computing features (no leakage of the current reading)
        for col in ROLLING_SOURCES:
            hist[col].append(r[col])
        self._last[aid] = {"heart_rate": r["heart_rate"], "sleep_hours": r["sleep_hours"]}
        self._last_ts[aid] = r["timestamp"]

        out["ml_ready"] = all(out.get(f) is not None for f in ML_FEATURES)
        return out
