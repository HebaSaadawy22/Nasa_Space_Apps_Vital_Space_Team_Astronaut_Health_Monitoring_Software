
"""Offline anomaly prediction for astronaut health readings."""

import json
from pathlib import Path

import joblib
import pandas as pd

from features import ENGINEERED, build_features


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "artifacts" / "anomaly_model.joblib"
DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"
OUTPUT_PATH = ROOT_DIR / "outputs" / "predictions.csv"

RESULT_COLUMNS = [
    "reading_id",
    "astronaut_id",
    "timestamp",
    "mission_day",
]


def load_model(model_path: Path):
    """Load a trusted, trained model bundle."""
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model not found: {model_path}"
        )

    return joblib.load(model_path)


def predict_history(
    raw: pd.DataFrame,
    model_path: Path = MODEL_PATH,
) -> pd.DataFrame:
    """Detect anomalies from historical astronaut readings."""
    bundle = load_model(Path(model_path))
    features = build_features(raw)

    results = features[RESULT_COLUMNS].copy()
    results["anomaly_detected"] = pd.Series(
        pd.NA,
        index=results.index,
        dtype="boolean",
    )
    results["anomaly_score"] = float("nan")
    results["model_status"] = "insufficient_history"

    feature_columns = bundle["features"]
    required_columns = list(
        dict.fromkeys(ENGINEERED + feature_columns)
    )
    valid_rows = features[required_columns].notna().all(axis=1)

    if not valid_rows.any():
        return results

    inputs = features.loc[valid_rows, feature_columns]
    pipeline = bundle["pipeline"]

    results.loc[valid_rows, "anomaly_detected"] = (
        pipeline.predict(inputs) == -1
    )
    results.loc[valid_rows, "anomaly_score"] = (
        -pipeline.decision_function(inputs)
    )
    results.loc[valid_rows, "model_status"] = "scored"

    return results


def summarize_predictions(results: pd.DataFrame) -> dict:
    """Return prediction counts."""
    status_counts = results["model_status"].value_counts()

    return {
        "total_readings": len(results),
        "scored": int(status_counts.get("scored", 0)),
        "insufficient_history": int(
            status_counts.get("insufficient_history", 0)
        ),
        "anomalies_detected": int(
            results["anomaly_detected"].fillna(False).sum()
        ),
    }


def main() -> None:
    raw = pd.read_csv(DATA_PATH)
    predictions = predict_history(raw)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT_PATH, index=False)

    print(predictions.tail(8).to_string(index=False))
    print(json.dumps(summarize_predictions(predictions), indent=2))
    print(f"Predictions saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()