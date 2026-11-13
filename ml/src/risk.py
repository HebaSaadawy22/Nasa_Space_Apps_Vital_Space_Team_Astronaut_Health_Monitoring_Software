
"""Operational risk assessment for Vital Space predictions."""

from collections.abc import Mapping, Sequence
from typing import Any


RISK_LEVELS = {"low", "moderate", "high"}
RISK_STATUS = "not_clinically_validated"
RISK_SCOPE = "experimental_review_priority"


def classify_review_priority(
    anomaly_detected: bool | None,
    model_status: str,
) -> str:
    """Determine whether an ML prediction needs review."""
    if model_status != "scored":
        return "pending_history"

    if anomaly_detected is None:
        return "unavailable"

    return (
        "review_required"
        if anomaly_detected
        else "no_model_flag"
    )


def validate_signals(
    signals: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Validate externally supplied rule signals."""
    validated = []
    seen_codes = set()

    for signal in signals:
        if not isinstance(signal, Mapping):
            raise ValueError("Each signal must be a mapping.")

        code = signal.get("code")
        level = signal.get("level")
        source = signal.get("source")

        if not all(
            isinstance(value, str) and value.strip()
            for value in (code, level, source)
        ):
            raise ValueError("Invalid risk signal fields.")

        if level not in {"moderate", "high"}:
            raise ValueError(f"Unsupported signal level: {level}")

        if code in seen_codes:
            raise ValueError(f"Duplicate signal code: {code}")

        seen_codes.add(code)

        validated.append(
            {
                "code": code,
                "level": level,
                "source": source,
            }
        )

    return validated


def assess_risk(
    anomaly_detected: bool | None,
    model_status: str,
    signals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Assign an experimental review level from available signals."""
    validated_signals = validate_signals(signals)

    reasons = []
    review_priority = classify_review_priority(
        anomaly_detected,
        model_status,
    )

    if model_status == "scored" and anomaly_detected is True:
        reasons.append("ml_anomaly_detected")

    if model_status != "scored":
        reasons.append("model_prediction_unavailable")

    if model_status == "scored" and anomaly_detected is None:
        reasons.append("missing_model_decision")

    reasons.extend(
        signal["code"]
        for signal in validated_signals
    )

    signal_levels = {
        signal["level"]
        for signal in validated_signals
    }

    if "high" in signal_levels:
        risk_level = "high"
    elif "moderate" in signal_levels:
        risk_level = "moderate"
    elif model_status != "scored" or anomaly_detected is None:
        risk_level = "unknown"
    elif anomaly_detected:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_reasons": reasons,
        "review_priority": review_priority,
        "risk_scope": RISK_SCOPE,
        "risk_assessment_status": RISK_STATUS,
    }


def enrich_prediction(
    prediction: dict[str, Any],
    signals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Append risk assessment metadata without changing ML outputs."""
    result = prediction.copy()

    assessment = assess_risk(
        anomaly_detected=result.get("anomaly_detected"),
        model_status=result.get("model_status", "unavailable"),
        signals=signals,
    )

    result.update(assessment)

    return result
