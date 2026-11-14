
"""Compare anomaly detection models on chronological data."""

import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import build_features


ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"
MODEL_PATH = ROOT_DIR / "artifacts" / "anomaly_model.joblib"
OUTPUT_DIR = ROOT_DIR / "outputs"

TRAIN_END_DAY = 18
VALIDATION_END_DAY = 23
CONTAMINATION = 0.08
RANDOM_STATE = 42

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

    # Load only trusted local model artifacts.
    bundle = joblib.load(MODEL_PATH)

    return raw, list(bundle["features"])


def build_models() -> dict:
    """Create reproducible anomaly detection pipelines."""
    return {
        "isolation_forest": make_pipeline(
            StandardScaler(),
            IsolationForest(
                n_estimators=200,
                contamination=CONTAMINATION,
                random_state=RANDOM_STATE,
            ),
        ),
        "local_outlier_factor": make_pipeline(
            StandardScaler(),
            LocalOutlierFactor(
                n_neighbors=20,
                contamination=CONTAMINATION,
                novelty=True,
            ),
        ),
    }


def prepare_data(
    raw: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create chronological training and validation splits."""
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
        raise ValueError("Training or validation data is empty.")

    if train[feature_columns].isna().any().any():
        raise ValueError("Training contains missing features.")

    if validation[feature_columns].isna().any().any():
        raise ValueError("Validation contains missing features.")

    return train, validation


def create_scenario(
    raw: pd.DataFrame,
    day: int,
    changes: dict,
) -> pd.DataFrame:
    """Modify one validation day without altering its history."""
    modified = raw.copy()
    mask = modified["mission_day"].eq(day)

    for column, delta in changes.items():
        modified.loc[mask, column] += delta

    modified.loc[mask, "spo2"] = (
        modified.loc[mask, "spo2"].clip(0, 100)
    )

    modified.loc[mask, "sleep_hours"] = (
        modified.loc[mask, "sleep_hours"].clip(0, 24)
    )

    return modified


def score_model(model, data: pd.DataFrame) -> pd.DataFrame:
    """Calculate anomaly flags and anomaly scores."""
    result = pd.DataFrame(index=data.index)

    result["anomaly_detected"] = model.predict(data) == -1
    result["anomaly_score"] = -model.decision_function(data)

    return result


def evaluate_model(
    model,
    raw: pd.DataFrame,
    validation: pd.DataFrame,
    feature_columns: list[str],
) -> dict:
    """Evaluate baseline and controlled synthetic changes."""
    baseline = score_model(
        model,
        validation[feature_columns],
    )

    target_day = VALIDATION_END_DAY
    target_mask = validation["mission_day"].eq(target_day)

    original = baseline.loc[target_mask].reset_index(drop=True)

    results = {
        "validation_rows": len(validation),
        "baseline_flagged": int(
            baseline["anomaly_detected"].sum()
        ),
        "scenarios": {},
    }

    for name, changes in SCENARIOS.items():
        modified_raw = create_scenario(
            raw,
            target_day,
            changes,
        )

        modified_features = build_features(modified_raw)

        target = modified_features.loc[
            modified_features["mission_day"].eq(target_day),
            feature_columns,
        ]

        modified = score_model(
            model,
            target,
        ).reset_index(drop=True)

        score_change = (
            modified["anomaly_score"]
            - original["anomaly_score"]
        )

        results["scenarios"][name] = {
            "samples": len(modified),
            "flagged_before": int(
                original["anomaly_detected"].sum()
            ),
            "flagged_after": int(
                modified["anomaly_detected"].sum()
            ),
            "mean_score_change": round(
                float(score_change.mean()),
                6,
            ),
            "increased_score_count": int(
                score_change.gt(0).sum()
            ),
        }

    return results


def compare_models() -> dict:
    """Train and compare models without replacing production artifacts."""
    raw, feature_columns = load_data()

    train, validation = prepare_data(
        raw,
        feature_columns,
    )

    results = {
        "train_rows": len(train),
        "validation_rows": len(validation),
        "train_days": [4, TRAIN_END_DAY],
        "validation_days": [
            TRAIN_END_DAY + 1,
            VALIDATION_END_DAY,
        ],
        "models": {},
        "limitations": (
            "Synthetic data without ground-truth labels. "
            "Results measure model sensitivity, not clinical accuracy. "
            "Previously inspected days 24-30 are not an untouched test set."
        ),
    }

    for name, model in build_models().items():
        model.fit(train[feature_columns])

        results["models"][name] = evaluate_model(
            model,
            raw,
            validation,
            feature_columns,
        )

    return results


def main() -> None:
    results = compare_models()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR / "model_comparison_summary.json"
    )

    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(results, indent=2))
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
