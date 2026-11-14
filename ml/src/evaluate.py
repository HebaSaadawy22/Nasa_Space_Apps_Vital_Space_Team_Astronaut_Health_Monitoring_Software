
"""Evaluate anomaly-score sensitivity on synthetic holdout readings."""

import json
from pathlib import Path

import pandas as pd

from predict import predict_history


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"
OUTPUT_DIR = ROOT_DIR / "outputs"
CUTOFF_DAY = 23

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


def modify_readings(
    raw: pd.DataFrame,
    day: int,
    changes: dict,
) -> pd.DataFrame:
    """Modify one holdout day without changing previous history."""
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


def evaluate_scenarios(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Compare original and modified holdout predictions."""
    baseline = predict_history(raw)

    train = baseline[baseline["mission_day"] <= CUTOFF_DAY]
    test = baseline[baseline["mission_day"] > CUTOFF_DAY]

    if train.empty or test.empty:
        raise ValueError("Training and holdout periods must exist")

    if not test["model_status"].eq("scored").all():
        raise ValueError("Holdout contains unscored readings")

    target_day = int(test["mission_day"].max())
    original = test[
        test["mission_day"] == target_day
    ].set_index("reading_id")

    comparisons = []

    for name, changes in SCENARIOS.items():
        modified_raw = modify_readings(raw, target_day, changes)
        modified = predict_history(modified_raw)

        modified = modified[
            modified["mission_day"] == target_day
        ].set_index("reading_id")

        if not modified["model_status"].eq("scored").all():
            raise ValueError(f"Unscored scenario: {name}")

        paired = original[
            ["astronaut_id", "anomaly_score", "anomaly_detected"]
        ].join(
            modified[["anomaly_score", "anomaly_detected"]],
            lsuffix="_before",
            rsuffix="_after",
            validate="one_to_one",
        ).reset_index()

        paired.insert(0, "scenario", name)

        paired["score_change"] = (
            paired["anomaly_score_after"]
            - paired["anomaly_score_before"]
        )

        comparisons.append(paired)

    details = pd.concat(comparisons, ignore_index=True)

    summary = {
        "test_rows": int(len(test)),
        "test_flagged": int(test["anomaly_detected"].sum()),
        "evaluation_day": target_day,
        "subjects_per_scenario": int(len(original)),
        "scenarios": {},
        "limitations": (
            "Synthetic perturbations are not ground-truth diagnoses. "
            "Score shifts do not measure clinical accuracy or recall."
        ),
    }

    for name, group in details.groupby("scenario", sort=False):
        summary["scenarios"][name] = {
            "flagged_before": int(
                group["anomaly_detected_before"].sum()
            ),
            "flagged_after": int(
                group["anomaly_detected_after"].sum()
            ),
            "mean_score_change": round(
                float(group["score_change"].mean()), 6
            ),
            "increased_score_count": int(
                group["score_change"].gt(0).sum()
            ),
        }

    return details, summary


def main() -> None:
    raw = pd.read_csv(DATA_PATH)
    details, summary = evaluate_scenarios(raw)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    details.to_csv(
        OUTPUT_DIR / "evaluation_details.csv",
        index=False,
    )

    (OUTPUT_DIR / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print("Saved evaluation_details.csv and evaluation_summary.json")


if __name__ == "__main__":
    main()
