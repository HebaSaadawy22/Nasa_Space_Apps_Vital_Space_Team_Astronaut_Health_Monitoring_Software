"""Core rules: turn raw readings into status levels and guidance."""
from __future__ import annotations

from typing import Mapping

from src.utils.constants import (
    ENVIRONMENTS,
    FIELDS,
    INDICATOR_BY_ID,
    INDICATORS,
    SYSTEMS,
)


def level(field: str, value: float) -> int:
    """0 = normal, 1 = watch, 2 = alert for one measured field."""
    f = FIELDS[field]
    if f["ok"][0] <= value <= f["ok"][1]:
        return 0
    if f["warn"][0] <= value <= f["warn"][1]:
        return 1
    return 2


def indicator_level(indicator_id: str, reading: Mapping[str, float]) -> int:
    ind = INDICATOR_BY_ID[indicator_id]
    return max(level(k, float(reading[k])) for k in ind["fields"])


def format_value(indicator_id: str, reading: Mapping[str, float]) -> str:
    ind = INDICATOR_BY_ID[indicator_id]
    return "/".join(f"{float(reading[k]):.{FIELDS[k]['dec']}f}" for k in ind["fields"])


def evaluate(reading: Mapping[str, float]) -> dict[str, dict]:
    """Evaluate every indicator for one reading."""
    return {
        ind["id"]: {
            "name": ind["name"],
            "value": format_value(ind["id"], reading),
            "unit": ind["unit"],
            "level": indicator_level(ind["id"], reading),
            "system": ind["system"],
        }
        for ind in INDICATORS
    }


def overall_level(reading: Mapping[str, float]) -> int:
    return max(v["level"] for v in evaluate(reading).values())


def count_by_level(reading: Mapping[str, float]) -> dict[int, int]:
    counts = {0: 0, 1: 0, 2: 0}
    for v in evaluate(reading).values():
        counts[v["level"]] += 1
    return counts


def system_level(system_id: str, reading: Mapping[str, float]) -> int:
    if system_id not in SYSTEMS:
        raise KeyError(system_id)
    levels = [v["level"] for v in evaluate(reading).values() if v["system"] == system_id]
    return max(levels) if levels else 0


def escalation_text(environment: str) -> str:
    return ENVIRONMENTS[environment]["escalation"]


def guidance(indicator_id: str, lvl: int, environment: str = "iss") -> dict:
    """Actions and explanation for one indicator at a given level."""
    ind = INDICATOR_BY_ID[indicator_id]
    if lvl == 0:
        actions = ["Within the normal range. Keep your routine."]
        note = ""
    elif lvl == 1:
        actions = ind["amber"]
        note = "Mention it at your next medical check-in and measure again tomorrow."
    else:
        actions = ind["red"]
        note = escalation_text(environment)
    return {"actions": actions, "note": note, "why": ind["why"], "how": ind["how"]}


def banner(reading: Mapping[str, float], environment: str = "iss") -> dict:
    counts = count_by_level(reading)
    worst = overall_level(reading)
    if worst == 0:
        title, text = "All indicators are in the normal range", "Keep your routine and log again tomorrow."
    elif worst == 1:
        n = counts[1]
        title = f"{n} indicator{'s' if n > 1 else ''} to watch"
        text = "Review the guidance and mention these at your next medical check-in."
    else:
        n = counts[2]
        title = f"{n} indicator{'s' if n > 1 else ''} need action"
        text = escalation_text(environment)
    return {"level": worst, "title": title, "text": text}
