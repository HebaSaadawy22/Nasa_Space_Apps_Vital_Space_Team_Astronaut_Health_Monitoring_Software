"""Generate simulated crew data. Run `python -m src.data.data_generator` to rebuild data/sample_health_data.csv."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.constants import FIELDS, ORDER

ROOT = Path(__file__).resolve().parents[2]

# start value, end value (drift over the period) per field
PROFILES = {
    "A01": {  # slow decline: blood pressure, glucose, sleep, exercise drift
        "hr": (62, 80), "sys": (118, 136), "dia": (76, 88), "glucose": (88, 106), "temp": (36.6, 37.2),
        "sleep": (7.4, 5.7), "mood": (4.2, 3.0), "spo2": (98, 95), "exercise": (110, 50)},
    "A02": {  # stable
        "hr": (58, 60), "sys": (114, 116), "dia": (72, 73), "glucose": (84, 86), "temp": (36.5, 36.6),
        "sleep": (7.6, 7.4), "mood": (4.5, 4.4), "spo2": (98, 98), "exercise": (120, 115)},
    "A03": {  # sleep and mood decline with an infection-like temperature rise at the end
        "hr": (66, 88), "sys": (120, 128), "dia": (78, 83), "glucose": (90, 98), "temp": (36.7, 37.8),
        "sleep": (7.1, 4.9), "mood": (4.0, 2.0), "spo2": (97, 94), "exercise": (100, 70)},
}


def generate(astronaut_id: str, days: int = 14, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed + sum(map(ord, astronaut_id)))
    prof = PROFILES[astronaut_id]
    rows = []
    for d in range(1, days + 1):
        t = (d - 1) / (days - 1)
        row = {"astronaut_id": astronaut_id, "day": d}
        for k in ORDER:
            a, b = prof[k]
            f = FIELDS[k]
            noise = rng.normal(0, 0.012 * abs(b - a) + 0.004 * (f["ok"][1] - f["ok"][0]))
            v = a + (b - a) * t + noise
            v = min(max(v, f["min"]), f["max"])
            row[k] = int(round(v)) if f["dec"] == 0 else round(float(v), f["dec"])
            if k == "exercise":
                row[k] = int(round(v / 5) * 5)
        rows.append(row)
    return pd.DataFrame(rows)


def build_all(days: int = 14) -> pd.DataFrame:
    return pd.concat([generate(a, days) for a in PROFILES], ignore_index=True)


def main() -> None:
    df = build_all()
    out = ROOT / "data" / "sample_health_data.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    crew = [
        {"id": "A01", "name": "Cmdr. Amira Hassan", "role": "Commander", "age": 41, "mission": "Mars transit simulation"},
        {"id": "A02", "name": "Dr. Kenji Mori", "role": "Flight surgeon (crew)", "age": 45, "mission": "Mars transit simulation"},
        {"id": "A03", "name": "Eng. Lena Novak", "role": "Flight engineer", "age": 36, "mission": "Mars transit simulation"},
    ]
    (ROOT / "data" / "astronauts.json").write_text(json.dumps(crew, indent=2))
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
