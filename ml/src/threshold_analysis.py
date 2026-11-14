
"""Analyze anomaly detection thresholds on chronological data."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import build_features


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"
MODEL_PATH = ROOT_DIR / "artifacts" / "anomaly_model.joblib"
OUTPUT_PATH = ROOT_DIR / "outputs" / "threshold_analysis.json"

TRAIN_END_DAY = 18
VALIDATION_END_DAY = 23
RANDOM_STATE = 42

QUANTILES = {
    "sensitive": 0.90,
    "moderate": 0.95,
    "conservative": 0.975,
    "very_conservative": 0.99,
}

SCENARIOS = {
    "high_heart_rate": {"heart_rate": 40},
    "low_oxygen": {"spo2": -8},
    "reduced_sleep": {"sleep_hours": -3},
    "combined_change": {
        "heart_rate": 40,
        "spo2": -8,
        "sleep_hours": -3,
    },
}


def load_data() -> tuple[pd.DataFrame, list[str]]:
    """Load raw readings and the existing feature contract."""
    raw = pd.read_csv(DATA_PATH)

    # Load only trusted model artifacts.
    bundle = joblib.load(MODEL_PATH)
    features = list(bundle["features"])

    if not features or len(features) != len(set(features)):
        raise ValueError("Invalid model feature contract.")

    return raw, features


def prepare_splits(
    raw: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build chronological training and validation datasets."""
    data = build_features(raw)

    train = data.loc[
        data["mission_day"].between(4, TRAIN_END_DAY)
    ].copy()

    validation = data.loc[
        data["mission_day"].between(
            TRAIN_END_DAY + 1,
            VALIDATION_END_DAY,
        )
    ].copy()

    for name, frame in (
        ("training", train),
        ("validation", validation),
    ):
        if frame.empty:
            raise ValueError(f"Empty {name} dataset.")

        if frame[columns].isna().any().any():
            raise ValueError(
                f"Missing features in {name} dataset."
            )

    return train, validation


def build_model():
    """Create an experimental model without changing saved artifacts."""
    return make_pipeline(
        StandardScaler(),
        IsolationForest(
            n_estimators=200,
            contamination=0.08,
            random_state=RANDOM_STATE,
        ),
    )


def anomaly_scores(model, data: pd.DataFrame) -> np.ndarray:
    """Return scores where larger values indicate more anomaly."""
    return -model.decision_function(data)


def calculate_thresholds(
    train_scores: np.ndarray,
) -> dict[str, float]:
    """Calculate thresholds using training scores only."""
    thresholds = {
        "model_default": 0.0,
    }

    for name, quantile in QUANTILES.items():
        thresholds[name] = float(
            np.quantile(train_scores, quantile)
        )

    return thresholds


def create_scenario(
    raw: pd.DataFrame,
    changes: dict[str, float],
) -> pd.DataFrame:
    """Modify final validation-day readings only."""
    modified = raw.copy()
    mask = modified["mission_day"].eq(VALIDATION_END_DAY)

    for column, delta in changes.items():
        modified.loc[mask, column] += delta

    modified.loc[mask, "spo2"] = (
        modified.loc[mask, "spo2"].clip(0, 100)
    )

    modified.loc[mask, "sleep_hours"] = (
        modified.loc[mask, "sleep_hours"].clip(0, 24)
    )

    return modified


def get_scenario_scores(
    model,
    raw: pd.DataFrame,
    columns: list[str],
) -> dict[str, pd.Series]:
    """Score modified validation readings by reading ID."""
    results = {}

    for name, changes in SCENARIOS.items():
        modified = create_scenario(raw, changes)
        features = build_features(modified)

        target = features.loc[
            features["mission_day"].eq(VALIDATION_END_DAY)
        ].set_index("reading_id")

        if target.empty or target[columns].isna().any().any():
            raise ValueError(f"Invalid scenario: {name}")

        scores = anomaly_scores(model, target[columns])

        results[name] = pd.Series(
            scores,
            index=target.index,
        )

    return results


def evaluate_thresholds(
    train_scores: np.ndarray,
    validation: pd.DataFrame,
    validation_scores: np.ndarray,
    scenario_scores: dict[str, pd.Series],
) -> dict:
    """Compare thresholds using paired simulated readings."""
    thresholds = calculate_thresholds(train_scores)

    baseline = pd.Series(
        validation_scores,
        index=validation["reading_id"],
    )

    target = validation.loc[
        validation["mission_day"].eq(VALIDATION_END_DAY)
    ]

    original = baseline.loc[target["reading_id"]]

    results = {}

    for name, threshold in thresholds.items():
        baseline_flags = baseline > threshold
        original_flags = original > threshold

        scenarios = {}

        for scenario_name, modified in scenario_scores.items():
            modified = modified.loc[original.index]
            modified_flags = modified > threshold

            newly_flagged = (
                modified_flags & ~original_flags
            )

            scenarios[scenario_name] = {
                "samples": int(len(modified)),
                "flagged_before": int(original_flags.sum()),
                "flagged_after": int(modified_flags.sum()),
                "newly_flagged": int(newly_flagged.sum()),
                "increased_score_count": int(
                    (modified > original).sum()
                ),
            }

        results[name] = {
            "threshold": round(threshold, 6),
            "validation_flagged": int(baseline_flags.sum()),
            "validation_flag_rate": round(
                float(baseline_flags.mean()),
                4,
            ),
            "scenarios": scenarios,
        }

    return results


def run_analysis() -> dict:
    """Train an experimental model and analyze its thresholds."""
    raw, columns = load_data()
    train, validation = prepare_splits(raw, columns)

    model = build_model()
    model.fit(train[columns])

    train_scores = anomaly_scores(
        model,
        train[columns],
    )

    validation_scores = anomaly_scores(
        model,
        validation[columns],
    )

    scenarios = get_scenario_scores(
        model,
        raw,
        columns,
    )

    return {
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "train_days": [4, TRAIN_END_DAY],
        "validation_days": [
            TRAIN_END_DAY + 1,
            VALIDATION_END_DAY,
        ],
        "feature_count": len(columns),
        "thresholds": evaluate_thresholds(
            train_scores,
            validation,
            validation_scores,
            scenarios,
        ),
        "limitations": (
            "Exploratory synthetic-data analysis only. "
            "Thresholds use training scores, but validation "
            "scenarios have been inspected previously. "
            "Flag rates do not measure false-positive rates "
            "without ground-truth labels."
        ),
    }


def main() -> None:
    report = run_analysis()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
