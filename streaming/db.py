"""PostgreSQL storage for processed readings and alerts."""
from __future__ import annotations

import json

import psycopg2
from psycopg2.extras import Json

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    reading_id TEXT PRIMARY KEY,
    astronaut_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    mission_day INT,
    heart_rate INT, systolic_bp INT, diastolic_bp INT, blood_glucose INT,
    body_temperature REAL, sleep_hours REAL, mood_score INT, activity_minutes INT, spo2 INT,
    cabin_co2_ppm INT, cabin_temp_c REAL, cabin_humidity_pct REAL, radiation_dose_rate REAL,
    ml_ready BOOLEAN, overall_level INT,
    features JSONB, prediction JSONB,
    received_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_readings_astro_ts ON readings (astronaut_id, ts);
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    reading_id TEXT NOT NULL,
    astronaut_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    indicator TEXT NOT NULL,
    value REAL, level INT NOT NULL,
    UNIQUE (reading_id, indicator)
);
"""

FEATURE_COLS = ["hr_rolling_3d", "sleep_rolling_3d", "systolic_rolling_3d", "mood_rolling_3d",
                "hr_change", "sleep_change", "hr_deviation", "sleep_deviation",
                "systolic_deviation", "mood_deviation"]


def connect(url: str | None = None):
    return psycopg2.connect(url or config.DB_URL)


def init_schema(conn) -> None:
    with conn, conn.cursor() as cur:
        cur.execute(SCHEMA)


def save(conn, rec: dict, overall: int, alerts: list[dict]) -> None:
    """Idempotent: re-sending the same reading_id does nothing."""
    features = {k: rec.get(k) for k in FEATURE_COLS}
    with conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO readings (reading_id, astronaut_id, ts, mission_day, heart_rate, systolic_bp,
                diastolic_bp, blood_glucose, body_temperature, sleep_hours, mood_score, activity_minutes, spo2,
                cabin_co2_ppm, cabin_temp_c, cabin_humidity_pct, radiation_dose_rate,
                ml_ready, overall_level, features, prediction)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (reading_id) DO NOTHING""",
            (rec["reading_id"], rec["astronaut_id"], rec["timestamp"], rec["mission_day"], rec["heart_rate"],
             rec["systolic_bp"], rec["diastolic_bp"], rec["blood_glucose"], rec["body_temperature"],
             rec["sleep_hours"], rec["mood_score"], rec["activity_minutes"], rec["spo2"],
             rec["cabin_co2_ppm"], rec["cabin_temp_c"], rec["cabin_humidity_pct"],
             rec["radiation_dose_rate_uSv_h"], rec["ml_ready"], overall,
             Json(features), Json(rec.get("prediction"))),
        )
        for a in alerts:
            cur.execute(
                """INSERT INTO alerts (reading_id, astronaut_id, ts, indicator, value, level)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (reading_id, indicator) DO NOTHING""",
                (rec["reading_id"], rec["astronaut_id"], rec["timestamp"], a["indicator"], a["value"], a["level"]),
            )
