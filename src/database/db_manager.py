"""SQLite storage for readings and daily tasks."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.utils.constants import ORDER

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "vital_space.db"


class DBManager:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = str(path)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        cols = ", ".join(f"{k} REAL NOT NULL" for k in ORDER)
        with self._conn() as c:
            c.execute(
                f"CREATE TABLE IF NOT EXISTS readings ("
                f"astronaut_id TEXT NOT NULL, day INTEGER NOT NULL, {cols}, "
                f"is_example INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (astronaut_id, day))"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS tasks ("
                "astronaut_id TEXT NOT NULL, day INTEGER NOT NULL, task_id TEXT NOT NULL, "
                "PRIMARY KEY (astronaut_id, day, task_id))"
            )

    # readings
    def count(self, astronaut_id: str | None = None) -> int:
        with self._conn() as c:
            if astronaut_id:
                return c.execute("SELECT COUNT(*) FROM readings WHERE astronaut_id=?", (astronaut_id,)).fetchone()[0]
            return c.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    def seed(self, df: pd.DataFrame) -> None:
        """Insert example rows (ignored if the day already exists)."""
        cols = ["astronaut_id", "day"] + ORDER
        with self._conn() as c:
            for r in df[cols].itertuples(index=False):
                c.execute(
                    f"INSERT OR IGNORE INTO readings ({','.join(cols)}, is_example) "
                    f"VALUES ({','.join('?' * len(cols))}, 1)",
                    tuple(r),
                )

    def add_reading(self, astronaut_id: str, reading: dict) -> int:
        """Add the next day for this astronaut and return the day number."""
        with self._conn() as c:
            last = c.execute("SELECT COALESCE(MAX(day), 0) FROM readings WHERE astronaut_id=?", (astronaut_id,)).fetchone()[0]
            day = last + 1
            cols = ["astronaut_id", "day"] + ORDER
            vals = [astronaut_id, day] + [float(reading[k]) for k in ORDER]
            c.execute(
                f"INSERT INTO readings ({','.join(cols)}, is_example) VALUES ({','.join('?' * len(cols))}, 0)", vals
            )
        return day

    def get_readings(self, astronaut_id: str) -> pd.DataFrame:
        with self._conn() as c:
            return pd.read_sql_query(
                "SELECT * FROM readings WHERE astronaut_id=? ORDER BY day", c, params=(astronaut_id,)
            )

    def reset(self, astronaut_id: str, example_df: pd.DataFrame) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM readings WHERE astronaut_id=?", (astronaut_id,))
            c.execute("DELETE FROM tasks WHERE astronaut_id=?", (astronaut_id,))
        self.seed(example_df[example_df["astronaut_id"] == astronaut_id])

    # tasks
    def done_tasks(self, astronaut_id: str, day: int) -> set[str]:
        with self._conn() as c:
            rows = c.execute("SELECT task_id FROM tasks WHERE astronaut_id=? AND day=?", (astronaut_id, day)).fetchall()
        return {r[0] for r in rows}

    def set_task(self, astronaut_id: str, day: int, task_id: str, done: bool) -> None:
        with self._conn() as c:
            if done:
                c.execute("INSERT OR IGNORE INTO tasks VALUES (?,?,?)", (astronaut_id, day, task_id))
            else:
                c.execute("DELETE FROM tasks WHERE astronaut_id=? AND day=? AND task_id=?", (astronaut_id, day, task_id))

    def streak(self, astronaut_id: str, task_points: dict[str, int], threshold: int = 80) -> int:
        """Consecutive most recent days with at least `threshold` task points."""
        with self._conn() as c:
            rows = c.execute("SELECT day, task_id FROM tasks WHERE astronaut_id=?", (astronaut_id,)).fetchall()
        per_day: dict[int, int] = {}
        for day, tid in rows:
            per_day[day] = per_day.get(day, 0) + task_points.get(tid, 0)
        if not per_day:
            return 0
        n, d = 0, max(per_day)
        while per_day.get(d, 0) >= threshold:
            n += 1
            d -= 1
        return n
