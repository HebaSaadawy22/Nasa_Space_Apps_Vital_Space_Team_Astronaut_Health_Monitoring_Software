
"""Incremental anomaly detection with configurable health rules."""

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from features import ENGINEERED, build_features
from health_rules import HealthRule, evaluate_health_rules
from risk import enrich_prediction
from validation import validate_raw_readings


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "artifacts" / "anomaly_model.joblib"
STATE_PATH = ROOT_DIR / "artifacts" / "stream_state.sqlite3"

HISTORY_SIZE = 3


class StreamingPredictor:
    """Score readings using persistent astronaut-specific history."""

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        state_path: Path = STATE_PATH,
        rules: Sequence[HealthRule] = (),
    ) -> None:
        self.bundle = joblib.load(model_path)
        self.state_path = Path(state_path)
        self.rules = tuple(rules)

        self.state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.db = sqlite3.connect(self.state_path)
        self.db.execute("PRAGMA busy_timeout = 5000")

        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create the database schema if it does not exist."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                reading_id TEXT PRIMARY KEY,
                astronaut_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(astronaut_id, timestamp)
            )
            """
        )

        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_readings_history
            ON readings(astronaut_id, timestamp DESC)
            """
        )

        self.db.commit()

    def _validate_message(
        self,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and normalize a raw sensor reading."""
        validated = validate_raw_readings(
            pd.DataFrame([message])
        )

        reading = validated.iloc[0].to_dict()
        reading["timestamp"] = pd.Timestamp(
            reading["timestamp"]
        ).isoformat()

        return reading

    def _check_reading(
        self,
        reading: dict[str, Any],
    ) -> None:
        """Reject duplicate IDs and out-of-order readings."""
        reading_id = reading["reading_id"]
        astronaut_id = reading["astronaut_id"]
        timestamp = reading["timestamp"]

        duplicate = self.db.execute(
            """
            SELECT 1
            FROM readings
            WHERE reading_id = ?
            """,
            (reading_id,),
        ).fetchone()

        if duplicate:
            raise ValueError(
                f"Duplicate reading_id: {reading_id}"
            )

        latest = self.db.execute(
            """
            SELECT timestamp
            FROM readings
            WHERE astronaut_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (astronaut_id,),
        ).fetchone()

        if latest and timestamp <= latest[0]:
            raise ValueError(
                f"Late or duplicate timestamp for {astronaut_id}"
            )

    def _get_history(
        self,
        astronaut_id: str,
    ) -> list[dict[str, Any]]:
        """Retrieve previous readings for one astronaut."""
        rows = self.db.execute(
            """
            SELECT payload
            FROM readings
            WHERE astronaut_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (astronaut_id, HISTORY_SIZE),
        ).fetchall()

        return [
            json.loads(row[0])
            for row in reversed(rows)
        ]

    def _enrich_with_rules(
        self,
        prediction: dict[str, Any],
        reading: dict[str, Any],
    ) -> dict[str, Any]:
        """Combine model output with configured rule signals."""
        signals = evaluate_health_rules(
            reading,
            self.rules,
        )

        return enrich_prediction(
            prediction,
            signals=signals,
        )

    def _predict(
        self,
        reading: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Predict anomalies and assess operational review priority."""
        features = build_features(
            pd.DataFrame(history + [reading])
        )

        latest = features.iloc[-1]

        prediction = {
            "reading_id": reading["reading_id"],
            "astronaut_id": reading["astronaut_id"],
            "timestamp": reading["timestamp"],
            "mission_day": int(reading["mission_day"]),
            "anomaly_detected": None,
            "anomaly_score": None,
            "model_status": "insufficient_history",
        }

        required = list(
            dict.fromkeys(
                ENGINEERED + self.bundle["features"]
            )
        )

        if latest[required].isna().any():
            return self._enrich_with_rules(
                prediction,
                reading,
            )

        inputs = features.iloc[-1:][
            self.bundle["features"]
        ]

        pipeline = self.bundle["pipeline"]

        prediction["anomaly_detected"] = bool(
            pipeline.predict(inputs)[0] == -1
        )

        prediction["anomaly_score"] = float(
            -pipeline.decision_function(inputs)[0]
        )

        prediction["model_status"] = "scored"

        return self._enrich_with_rules(
            prediction,
            reading,
        )

    def _save_reading(
        self,
        reading: dict[str, Any],
    ) -> None:
        """Persist an accepted reading."""
        self.db.execute(
            """
            INSERT INTO readings (
                reading_id,
                astronaut_id,
                timestamp,
                payload
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                reading["reading_id"],
                reading["astronaut_id"],
                reading["timestamp"],
                json.dumps(reading),
            ),
        )

    def process(
        self,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate, score, assess, and persist one reading."""
        reading = self._validate_message(message)

        with self.db:
            self.db.execute("BEGIN IMMEDIATE")

            self._check_reading(reading)

            history = self._get_history(
                reading["astronaut_id"]
            )

            result = self._predict(
                reading,
                history,
            )

            self._save_reading(reading)

        return result

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()

    def __enter__(self) -> "StreamingPredictor":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
