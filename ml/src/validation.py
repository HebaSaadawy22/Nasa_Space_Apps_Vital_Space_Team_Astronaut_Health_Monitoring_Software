
"""Validate raw astronaut readings before model inference."""

import re
from collections.abc import Mapping

import pandas as pd


REQUIRED_COLUMNS = (
    "reading_id",
    "astronaut_id",
    "timestamp",
    "mission_day",
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "blood_glucose",
    "glucose_context",
    "body_temperature",
    "sleep_hours",
    "mood_score",
    "activity_minutes",
    "spo2",
    "cabin_co2_ppm",
    "cabin_temp_c",
    "cabin_humidity_pct",
    "radiation_dose_rate_uSv_h",
    "data_source",
)

RANGES = {
    "mission_day": (1, None),
    "heart_rate": (1, 300),
    "systolic_bp": (1, 300),
    "diastolic_bp": (1, 250),
    "blood_glucose": (1, 1000),
    "body_temperature": (25, 45),
    "sleep_hours": (0, 24),
    "mood_score": (1, 5),
    "activity_minutes": (0, 1440),
    "spo2": (0, 100),
    "cabin_co2_ppm": (0, 100000),
    "cabin_temp_c": (-50, 80),
    "cabin_humidity_pct": (0, 100),
    "radiation_dose_rate_uSv_h": (0, None),
}

INTEGER_COLUMNS = (
    "mission_day",
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "blood_glucose",
    "mood_score",
    "activity_minutes",
    "spo2",
    "cabin_co2_ppm",
)

TEXT_COLUMNS = (
    "reading_id",
    "astronaut_id",
    "glucose_context",
    "data_source",
)

TIMEZONE_PATTERN = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


class DataValidationError(ValueError):
    """Raised when incoming data violates the input contract."""


def validate_raw_readings(
    raw: pd.DataFrame,
    last_seen: Mapping | None = None,
) -> pd.DataFrame:
    """Validate readings and return a chronological copy."""
    if not isinstance(raw, pd.DataFrame):
        raise DataValidationError("Input must be a DataFrame.")

    if raw.empty:
        raise DataValidationError("Input dataset is empty.")

    missing_columns = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing_columns:
        raise DataValidationError(
            f"Missing columns: {sorted(missing_columns)}"
        )

    data = raw.loc[:, REQUIRED_COLUMNS].copy()

    if data.isna().any().any():
        raise DataValidationError("Missing values detected.")

    for column in TEXT_COLUMNS:
        values = data[column]

        if not values.map(
            lambda value: (
                isinstance(value, str) and bool(value.strip())
            )
        ).all():
            raise DataValidationError(
                f"Invalid text values in {column}."
            )

    for column, (lower, upper) in RANGES.items():
        try:
            values = pd.to_numeric(data[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise DataValidationError(
                f"Invalid numeric values in {column}."
            ) from exc

        if not values.notna().all():
            raise DataValidationError(
                f"Invalid numeric values in {column}."
            )

        if not values.between(
            lower if lower is not None else float("-inf"),
            upper if upper is not None else float("inf"),
        ).all():
            raise DataValidationError(
                f"Values outside technical range in {column}."
            )

        if column in INTEGER_COLUMNS:
            if not values.map(
                lambda value: float(value).is_integer()
            ).all():
                raise DataValidationError(
                    f"Expected integers in {column}."
                )

        data[column] = values

    if data["reading_id"].duplicated().any():
        raise DataValidationError("Duplicate reading_id detected.")

    timestamps = []

    for value in data["timestamp"]:
        if isinstance(value, str):
            if not TIMEZONE_PATTERN.search(value.strip()):
                raise DataValidationError(
                    "Timestamp must include a UTC timezone."
                )

        try:
            parsed = pd.Timestamp(value)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(
                "Invalid timestamp."
            ) from exc

        if pd.isna(parsed) or parsed.tzinfo is None:
            raise DataValidationError(
                "Timestamp must be timezone-aware."
            )

        if parsed.utcoffset().total_seconds() != 0:
            raise DataValidationError(
                "Timestamp must be in UTC."
            )

        timestamps.append(parsed.tz_convert("UTC"))

    data["timestamp"] = pd.DatetimeIndex(timestamps)

    if data.duplicated(
        subset=["astronaut_id", "timestamp"]
    ).any():
        raise DataValidationError(
            "Duplicate astronaut timestamp detected."
        )

    if last_seen:
        for astronaut_id, group in data.groupby("astronaut_id"):
            if astronaut_id not in last_seen:
                continue

            previous = pd.Timestamp(last_seen[astronaut_id])

            if previous.tzinfo is None:
                raise DataValidationError(
                    "last_seen timestamps must include a timezone."
                )

            previous = previous.tz_convert("UTC")

            if group["timestamp"].min() <= previous:
                raise DataValidationError(
                    f"Late or repeated reading for {astronaut_id}."
                )

    return data.sort_values(
        ["astronaut_id", "timestamp", "reading_id"],
        kind="stable",
    ).reset_index(drop=True)
