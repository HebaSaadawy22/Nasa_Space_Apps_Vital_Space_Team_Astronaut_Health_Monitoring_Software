
"""Compare feature groups for astronaut anomaly detection."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import build_features


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"
MODEL_PATH = ROOT_DIR / "artifacts" / "anomaly_model.joblib"
OUTPUT_PATH = ROOT_DIR / "outputs" / "feature_experiments.json"

TRAIN_END_DAY = 18
VALIDATION_END_DAY = 23
RANDOM_STATE = 42

ENVIRONMENT_FEATURES = [
    "cabin_co2_ppm",
    "cabin_temp_c",
    "cabin_humidity_pct",
    "radiation_dose_rate_uSv_h",
]

SELECTED_ENVIRONMENT_FEATURES = [
    "cabin_co2_ppm",
    "radiation_dose_rate_uSv_h",
]

SCENARIOS = {
    "high_heart_rate": {"heart_rate": 40},
    "low_oxygen": {"spo2": -8},
    "high_co2": {"cabin_co2_ppm": 700},
    "high_radiation": {
        "radiation_dose_rate_uSv_h": 0.5,
    },
    "combined_change": {
        "heart_rate": 40,
        "spo2": -8,
        "cabin_co2_ppm": 700,
    },
}


def load_inputs() -> tuple[pd.DataFrame, list[str]]:
    """Load raw data and the existing model feature contract."""
    raw = pd.read_csv(DATA_PATH)

    # Only load trusted local artifacts.
    bundle = joblib.load(MODEL_PATH)
    baseline_features = list(bundle["features"])

    if len(baseline_features) != len(set(baseline_features)):
        raise ValueError("Duplicate baseline feature names.")

    return raw, baseline_features


def build_feature_groups(
    baseline: list[str],
) -> dict[str, list[str]]:
    """Create feature groups without duplicate columns."""
    return {
        "baseline": baseline.copy(),
        "all_environment": list(
            dict.fromkeys(baseline + ENVIRONMENT_FEATURES)
        ),
        "selected_environment": list(
            dict.fromkeys(
                baseline + SELECTED_ENVIRONMENT_FEATURES
            )
        ),
    }


def prepare_data(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create chronological training and validation sets."""
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

    if train.empty or validation.empty:
        raise ValueError("Empty training or validation split.")

    if train["reading_id"].duplicated().any():
        raise ValueError("Duplicate training reading IDs.")

    if validation["reading_id"].duplicated().any():
        raise ValueError("Duplicate validation reading IDs.")

    return train, validation


def validate_features(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    columns: list[str],
) -> None:
    """Check that selected features are numeric and complete."""
    for name, data in (
        ("training", train),
        ("validation", validation),
    ):
        missing = set(columns) - set(data.columns)

        if missing:
            raise ValueError(
                f"Missing {name} features: {sorted(missing)}"
            )

        selected = data[columns]

        if selected.isna().any().any():
            raise ValueError(
                f"Missing values in {name} features."
            )

        if not all(
            pd.api.types.is_numeric_dtype(dtype)
            for dtype in selected.dtypes
        ):
            raise ValueError(
                f"Non-numeric features in {name} data."
            )


def create_model():
    """Build an Isolation Forest pipeline for experimentation."""
    return make_pipeline(
        StandardScaler(),
        IsolationForest(
            n_estimators=200,
            contamination=0.08,
            random_state=RANDOM_STATE,
        ),
    )


def predict_scores(model, data: pd.DataFrame) -> pd.DataFrame:
    """Return model anomaly flags and signed anomaly scores."""
    return pd.DataFrame(
        {
            "anomaly_detected": model.predict(data) == -1,
            "anomaly_score": -model.decision_function(data),
        }
    )


def create_scenario(
    raw: pd.DataFrame,
    changes: dict[str, float],
) -> pd.DataFrame:
    """Modify the final validation day without changing history."""
    modified = raw.copy()
    mask = modified["mission_day"].eq(VALIDATION_END_DAY)

    for column, delta in changes.items():
        modified.loc[mask, column] += delta

    modified.loc[mask, "spo2"] = (
        modified.loc[mask, "spo2"].clip(0, 100)
    )

    return modified


def evaluate_scenarios(
    model,
    raw: pd.DataFrame,
    validation: pd.DataFrame,
    columns: list[str],
) -> dict:
    """Compare original and modified readings by reading ID."""
    day_mask = validation["mission_day"].eq(
        VALIDATION_END_DAY
    )

    original = validation.loc[day_mask].copy()

    baseline_scores = predict_scores(
        model,
        original[columns],
    )

    baseline_scores.index = original["reading_id"].to_numpy()

    results = {}

    for name, changes in SCENARIOS.items():
        modified_raw = create_scenario(raw, changes)
        modified_features = build_features(modified_raw)

        target = modified_features.loc[
            modified_features["mission_day"].eq(
                VALIDATION_END_DAY
            )
        ].copy()

        target = target.set_index("reading_id")
        target = target.loc[baseline_scores.index]

        modified_scores = predict_scores(
            model,
            target[columns],
        )

        modified_scores.index = target.index

        score_changes = (
            modified_scores["anomaly_score"]
            - baseline_scores["anomaly_score"]
        )

        newly_flagged = (
            modified_scores["anomaly_detected"]
            & ~baseline_scores["anomaly_detected"]
        )

        results[name] = {
            "samples": int(len(target)),
            "flagged_before": int(
                baseline_scores["anomaly_detected"].sum()
            ),
            "flagged_after": int(
                modified_scores["anomaly_detected"].sum()
            ),
            "newly_flagged": int(newly_flagged.sum()),
            "increased_score_count": int(
                score_changes.gt(0).sum()
            ),
            "mean_score_change": round(
                float(score_changes.mean()),
                6,
            ),
        }

    return results


def run_experiments() -> dict:
    """Train and evaluate each feature configuration."""
    raw, baseline = load_inputs()
    train, validation = prepare_data(raw)

    groups = build_feature_groups(baseline)

    report = {
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "train_days": [4, TRAIN_END_DAY],
        "validation_days": [
            TRAIN_END_DAY + 1,
            VALIDATION_END_DAY,
        ],
        "experiments": {},
        "limitations": (
            "Synthetic data without ground-truth labels. "
            "Results describe anomaly sensitivity, not "
            "clinical performance. The validation period "
            "has been explored previously."
        ),
    }

    for name, columns in groups.items():
        validate_features(train, validation, columns)

        model = create_model()
        model.fit(train[columns])

        validation_scores = predict_scores(
            model,
            validation[columns],
        )

        report["experiments"][name] = {
            "feature_count": len(columns),
            "added_features": [
                column
                for column in columns
                if column not in baseline
            ],
            "baseline_flagged": int(
                validation_scores["anomaly_detected"].sum()
            ),
            "scenarios": evaluate_scenarios(
                model,
                raw,
                validation,
                columns,
            ),
        }

    return report


def main() -> None:
    report = run_experiments()

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
