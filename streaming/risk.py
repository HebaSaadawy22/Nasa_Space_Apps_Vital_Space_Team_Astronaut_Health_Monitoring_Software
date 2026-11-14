"""Rule-based status per reading, reusing the project's own reference ranges (src/utils/constants.py).

0 = Normal, 1 = Watch, 2 = Alert. Demonstration only, not medical advice.
"""
from __future__ import annotations

from src.analysis.health_engine import level
from src.utils.constants import FIELDS

# raw column -> key used in constants.FIELDS
FIELD_MAP = {
    "heart_rate": "hr", "systolic_bp": "sys", "diastolic_bp": "dia", "blood_glucose": "glucose",
    "body_temperature": "temp", "sleep_hours": "sleep", "mood_score": "mood", "spo2": "spo2",
}


def assess(record: dict) -> tuple[int, list[dict]]:
    """Return (overall_level, alerts). Alerts are the indicators that are not Normal."""
    alerts = []
    for col, key in FIELD_MAP.items():
        lvl = level(key, record[col])
        if lvl > 0:
            alerts.append({"indicator": FIELDS[key]["label"], "column": col, "value": record[col], "level": lvl})
    overall = max([a["level"] for a in alerts], default=0)
    return overall, alerts
