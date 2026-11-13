"""Load crew list, sample data and the shared database."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.database.db_manager import DBManager

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def load_astronauts() -> list[dict]:
    return json.loads((DATA_DIR / "astronauts.json").read_text())


def load_sample_csv() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sample_health_data.csv")


@lru_cache(maxsize=1)
def get_db() -> DBManager:
    """Shared database, seeded from the sample CSV the first time."""
    db = DBManager()
    if db.count() == 0:
        db.seed(load_sample_csv())
    return db


def get_readings(astronaut_id: str) -> pd.DataFrame:
    return get_db().get_readings(astronaut_id)


def reset_astronaut(astronaut_id: str) -> None:
    get_db().reset(astronaut_id, load_sample_csv())
