"""Shared settings for the streaming pipeline (override with environment variables)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_RAW = os.getenv("TOPIC_RAW", "astronaut.vitals.raw")
TOPIC_PROCESSED = os.getenv("TOPIC_PROCESSED", "astronaut.vitals.processed")
TOPIC_DEAD_LETTER = os.getenv("TOPIC_DEAD_LETTER", "astronaut.vitals.invalid")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "vital-space-consumer")

RAW_CSV = Path(os.getenv("RAW_CSV", ROOT / "astronaut_kafka_raw.csv"))

# Raw fields a sensor/simulator is allowed to send (no precomputed features).
RAW_FIELDS = [
    "reading_id", "astronaut_id", "timestamp", "mission_day",
    "heart_rate", "systolic_bp", "diastolic_bp", "blood_glucose", "glucose_context",
    "body_temperature", "sleep_hours", "mood_score", "activity_minutes", "spo2",
    "cabin_co2_ppm", "cabin_temp_c", "cabin_humidity_pct", "radiation_dose_rate_uSv_h",
    "data_source",
]

# Technical plausibility ranges (NOT medical thresholds) - same as data_preprocessing.ipynb
VALID_RANGES = {
    "heart_rate": (20, 250),
    "systolic_bp": (50, 260),
    "diastolic_bp": (20, 180),
    "blood_glucose": (20, 600),
    "body_temperature": (30, 43),
    "sleep_hours": (0, 24),
    "mood_score": (1, 5),
    "activity_minutes": (0, 1440),
    "spo2": (0, 100),
    "cabin_co2_ppm": (0, 100000),
    "cabin_temp_c": (-20, 60),
    "cabin_humidity_pct": (0, 100),
    "radiation_dose_rate_uSv_h": (0, float("inf")),
}

# Feature engineering (same definitions as the notebook)
ROLLING_WINDOW = 3
ROLLING_SOURCES = {  # raw column -> prefix
    "heart_rate": "hr",
    "sleep_hours": "sleep",
    "systolic_bp": "systolic",
    "mood_score": "mood",
}
# Column order the ML model expects (matches the notebook's ml_features)
ML_FEATURES = [
    "heart_rate", "systolic_bp", "diastolic_bp", "blood_glucose", "body_temperature",
    "sleep_hours", "mood_score", "activity_minutes", "spo2",
    "hr_rolling_3d", "sleep_rolling_3d", "systolic_rolling_3d", "mood_rolling_3d",
    "hr_change", "sleep_change",
    "hr_deviation", "sleep_deviation", "systolic_deviation", "mood_deviation",
]

# PostgreSQL (matches docker-compose.yml)
DB_URL = os.getenv("DB_URL", "postgresql://vitalspace:vitalspace@localhost:5432/vitalspace")

# ML team's model (folder `ml/` from branch feature/machine-learning)
ML_DIR = ROOT / "ml"
ML_STATE_PATH = Path(os.getenv("ML_STATE_PATH", ROOT / "ml" / "artifacts" / "stream_state.sqlite3"))
