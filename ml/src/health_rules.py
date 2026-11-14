
"""Configurable, non-clinical health monitoring rules."""

import math
import operator
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


ALLOWED_METRICS = frozenset({
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "blood_glucose",
    "body_temperature",
    "sleep_hours",
    "mood_score",
    "activity_minutes",
    "spo2",
    "cabin_co2_ppm",
    "cabin_temp_c",
    "cabin_humidity_pct",
    "radiation_dose_rate_uSv_h",
})

OPERATORS = {
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
}


@dataclass(frozen=True)
class HealthRule:
    """A configurable condition requiring documented approval."""

    code: str
    metric: str
    operator: str
    threshold: float
    level: str
    source: str

    def __post_init__(self) -> None:
        for field in ("code", "source"):
            value = getattr(self, field)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid rule field: {field}")

        if self.metric not in ALLOWED_METRICS:
            raise ValueError(f"Unsupported metric: {self.metric}")

        if self.operator not in OPERATORS:
            raise ValueError(f"Unsupported operator: {self.operator}")

        if self.level not in {"moderate", "high"}:
            raise ValueError(f"Unsupported level: {self.level}")

        if (
            isinstance(self.threshold, bool)
            or not isinstance(self.threshold, (int, float))
            or not math.isfinite(self.threshold)
        ):
            raise ValueError("Threshold must be a finite number.")


def evaluate_health_rules(
    reading: Mapping[str, Any],
    rules: Sequence[HealthRule] = (),
) -> list[dict[str, str]]:
    """Return triggered review signals for one validated reading."""
    signals = []
    seen_codes = set()

    for rule in rules:
        if not isinstance(rule, HealthRule):
            raise TypeError("Expected HealthRule instances.")

        if rule.code in seen_codes:
            raise ValueError(f"Duplicate rule code: {rule.code}")

        seen_codes.add(rule.code)

        if rule.metric not in reading:
            raise ValueError(f"Missing metric: {rule.metric}")

        value = reading[rule.metric]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Invalid metric: {rule.metric}")

        condition = OPERATORS[rule.operator]

        if condition(value, rule.threshold):
            signals.append({
                "code": rule.code,
                "level": rule.level,
                "source": rule.source,
            })

    return signals
