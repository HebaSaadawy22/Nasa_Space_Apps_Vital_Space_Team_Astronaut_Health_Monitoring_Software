"""Validation of one raw reading. Returns a list of error strings (empty = valid)."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from .config import RAW_FIELDS, VALID_RANGES


def parse_timestamp(value) -> datetime:
    """Parse ISO 8601 into a timezone-aware UTC datetime (naive input is treated as UTC)."""
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_reading(r: dict) -> list[str]:
    errors: list[str] = []

    missing = [f for f in RAW_FIELDS if r.get(f) in (None, "")]
    if missing:
        return [f"missing fields: {', '.join(missing)}"]

    try:
        parse_timestamp(r["timestamp"])
    except (ValueError, TypeError):
        errors.append("invalid timestamp")

    try:
        if int(r["mission_day"]) < 1:
            errors.append("mission_day must be >= 1")
    except (ValueError, TypeError):
        errors.append("mission_day is not an integer")

    for col, (lo, hi) in VALID_RANGES.items():
        try:
            v = float(r[col])
        except (ValueError, TypeError):
            errors.append(f"{col} is not numeric")
            continue
        if math.isnan(v) or not (lo <= v <= hi):
            errors.append(f"{col}={r[col]} outside plausible range [{lo}, {hi}]")

    try:
        if float(r["systolic_bp"]) <= float(r["diastolic_bp"]):
            errors.append("systolic_bp must be greater than diastolic_bp")
    except (ValueError, TypeError):
        pass  # already reported above

    return errors
