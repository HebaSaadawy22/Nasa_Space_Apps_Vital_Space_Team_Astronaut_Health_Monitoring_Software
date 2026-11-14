"""Causal, astronaut-specific features matching data_preprocessing.ipynb."""
import pandas as pd

RAW_REQUIRED = ["reading_id", "astronaut_id", "timestamp", "mission_day",
                "heart_rate", "systolic_bp", "sleep_hours", "mood_score"]
ROLLING = {"heart_rate": "hr", "sleep_hours": "sleep",
           "systolic_bp": "systolic", "mood_score": "mood"}
ENGINEERED = ["hr_rolling_3d", "sleep_rolling_3d", "systolic_rolling_3d",
              "mood_rolling_3d", "hr_change", "sleep_change", "hr_deviation",
              "sleep_deviation", "systolic_deviation", "mood_deviation"]

def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    missing = set(RAW_REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing raw columns: {sorted(missing)}")
    df = raw.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="raise")
    if df["reading_id"].duplicated().any():
        raise ValueError("Duplicate reading_id")
    if df.duplicated(["astronaut_id", "timestamp"]).any():
        raise ValueError("Duplicate astronaut timestamp")
    df = df.sort_values(["astronaut_id", "timestamp", "reading_id"]).reset_index(drop=True)
    grouped = df.groupby("astronaut_id", sort=False)
    for col, prefix in ROLLING.items():
        df[f"{prefix}_rolling_3d"] = grouped[col].transform(
            lambda s: s.shift(1).rolling(3, min_periods=3).mean())
        df[f"{prefix}_deviation"] = df[col] - df[f"{prefix}_rolling_3d"]
    df["hr_change"] = grouped["heart_rate"].diff()
    df["sleep_change"] = grouped["sleep_hours"].diff()
    return df
