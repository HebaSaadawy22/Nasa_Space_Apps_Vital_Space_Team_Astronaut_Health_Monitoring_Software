"""Offline anomaly detection demo. No medical labels or clinical claims."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from features import build_features, ENGINEERED

ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "heart_rate", "systolic_bp", "diastolic_bp", "blood_glucose",
    "body_temperature", "sleep_hours", "mood_score", "activity_minutes",
    "spo2", "hr_rolling_3d", "sleep_rolling_3d", "systolic_rolling_3d",
    "mood_rolling_3d", "hr_change", "sleep_change", "hr_deviation",
    "sleep_deviation", "systolic_deviation", "mood_deviation"
]
CUTOFF_DAY = 23

def main():
    raw = pd.read_csv(ROOT / "data/astronaut_kafka_raw.csv")
    existing = pd.read_csv(ROOT / "data/astronaut_ml_ready.csv")
    prepared = build_features(raw).dropna(subset=ENGINEERED).copy()
    # Data consistency check: detect a drift between offline and streaming recipes.
    left = prepared.set_index("reading_id").sort_index()
    right = existing.set_index("reading_id").sort_index()
    if set(left.index) != set(right.index):
        raise ValueError("Raw-derived rows disagree with ML-ready dataset")
    for feature in FEATURES:
        if not np.allclose(left[feature].to_numpy(dtype=float),
                           right[feature].to_numpy(dtype=float), rtol=1e-9, atol=1e-9):
            raise ValueError(f"Raw-derived feature mismatch: {feature}")
    prepared = prepared.sort_values(["mission_day", "astronaut_id", "timestamp"])
    train = prepared[prepared["mission_day"] <= CUTOFF_DAY].copy()
    test = prepared[prepared["mission_day"] > CUTOFF_DAY].copy()
    if train.empty or test.empty or train["mission_day"].max() >= test["mission_day"].min():
        raise ValueError("Invalid chronological split")
    if train[FEATURES].isna().any().any() or test[FEATURES].isna().any().any():
        raise ValueError("Missing model input values")
    # 0.08 is a demonstration assumption, not a learned prevalence or clinical threshold.
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("detector", IsolationForest(n_estimators=200, contamination=0.08,
                                      random_state=42, n_jobs=1))
    ])
    model.fit(train[FEATURES])
    def score(frame, split):
        result = frame[["reading_id", "astronaut_id", "timestamp", "mission_day"]].copy()
        result["split"] = split
        result["anomaly_score"] = -model.decision_function(frame[FEATURES])
        result["anomaly_detected"] = model.predict(frame[FEATURES]) == -1
        result["model_status"] = "scored"
        return result
    out = pd.concat([score(train, "train"), score(test, "test")], ignore_index=True)
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "outputs").mkdir(exist_ok=True)
    joblib.dump({"pipeline": model, "features": FEATURES,
                 "schema_version": "1.0", "min_previous_readings": 3},
                ROOT / "artifacts/anomaly_model.joblib")
    out.to_csv(ROOT / "outputs/predictions.csv", index=False)
    summary = {"train_rows": len(train), "test_rows": len(test),
               "train_days": [int(train.mission_day.min()), int(train.mission_day.max())],
               "test_days": [int(test.mission_day.min()), int(test.mission_day.max())],
               "train_flagged": int(out.loc[out.split == "train", "anomaly_detected"].sum()),
               "test_flagged": int(out.loc[out.split == "test", "anomaly_detected"].sum()),
               "note": "Unsupervised demo only: no ground-truth anomaly labels or clinical validation."}
    (ROOT / "outputs/summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("Saved artifacts/anomaly_model.joblib and outputs/predictions.csv")

if __name__ == "__main__":
    main()
