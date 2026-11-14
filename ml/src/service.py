
"""Prediction interface for the Vital Space monitoring system."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from predict import predict_history
from risk import enrich_prediction
from validation import validate_raw_readings
from collections.abc import Sequence
from health_rules import HealthRule, evaluate_health_rules
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"


def serialize_prediction(row: pd.Series) -> dict[str, Any]:
    """Convert a prediction row into a JSON-compatible record."""
    anomaly = row["anomaly_detected"]
    score = row["anomaly_score"]

    prediction = {
        "reading_id": str(row["reading_id"]),
        "astronaut_id": str(row["astronaut_id"]),
        "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
        "mission_day": int(row["mission_day"]),
        "anomaly_detected": (
            None if pd.isna(anomaly) else bool(anomaly)
        ),
        "anomaly_score": (
            None if pd.isna(score) else float(score)
        ),
        "model_status": str(row["model_status"]),
    }

    return enrich_prediction(prediction)





def predict_readings(
    raw: pd.DataFrame,
    rules: Sequence[HealthRule] = (),
) -> list[dict[str, Any]]:
    """Validate readings and combine ML with rule signals."""
    validated = validate_raw_readings(raw)
    predictions = predict_history(validated)

    readings_by_id = validated.set_index("reading_id")

    results = []

    for _, row in predictions.iterrows():
        prediction = serialize_prediction(row)

        reading = readings_by_id.loc[
            prediction["reading_id"]
        ].to_dict()

        signals = evaluate_health_rules(reading, rules)

        results.append(
            enrich_prediction(prediction, signals=signals)
        )

    return results


def predict_latest(
    raw: pd.DataFrame,
    astronaut_id: str,
    rules: Sequence[HealthRule] = (),
) -> dict[str, Any]:
    """Return the latest assessment for an astronaut."""
    predictions = predict_readings(raw, rules=rules)

    astronaut_predictions = [
        prediction
        for prediction in predictions
        if prediction["astronaut_id"] == astronaut_id
    ]

    if not astronaut_predictions:
        raise ValueError(
            f"No readings found for astronaut: {astronaut_id}"
        )

    return max(
        astronaut_predictions,
        key=lambda prediction: prediction["timestamp"],
    )


def main() -> None:
    raw = pd.read_csv(DATA_PATH)

    result = predict_latest(raw, "AST001")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
