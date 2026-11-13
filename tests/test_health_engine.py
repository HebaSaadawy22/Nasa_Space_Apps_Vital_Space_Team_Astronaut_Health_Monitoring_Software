import pandas as pd
import pytest

from src.analysis import health_engine as he
from src.analysis.baseline import deviations
from src.analysis.risk_assessment import hazard_scores, trend_report
from src.data.data_generator import build_all
from src.database.db_manager import DBManager

NORMAL = dict(hr=62, sys=118, dia=76, glucose=88, temp=36.6, sleep=7.5, mood=4, spo2=98, exercise=110)


def test_level_boundaries():
    assert he.level("hr", 50) == 0 and he.level("hr", 90) == 0
    assert he.level("hr", 95) == 1
    assert he.level("hr", 115) == 2 and he.level("hr", 35) == 2
    assert he.level("temp", 37.2) == 0 and he.level("temp", 38.0) == 2


def test_blood_pressure_uses_worst_of_two_values():
    r = dict(NORMAL, sys=120, dia=95)
    assert he.indicator_level("bp", r) == 2
    assert he.format_value("bp", r) == "120/95"


def test_all_normal():
    assert he.overall_level(NORMAL) == 0
    assert he.banner(NORMAL)["title"].startswith("All indicators")


def test_alert_banner_uses_environment_text():
    r = dict(NORMAL, spo2=89)
    assert he.banner(r, "mars")["level"] == 2
    assert "44 minutes" in he.banner(r, "mars")["text"]
    assert "1.3 seconds" in he.banner(r, "moon")["text"]


def test_system_level_and_unknown_system():
    assert he.system_level("lungs", dict(NORMAL, spo2=93)) == 1
    with pytest.raises(KeyError):
        he.system_level("liver", NORMAL)


def test_guidance_levels():
    assert "Keep your routine" in he.guidance("hr", 0)["actions"][0]
    assert he.guidance("hr", 2, "iss")["note"]


def test_sample_data_shape_and_ranges():
    df = build_all()
    assert len(df) == 42 and set(df.astronaut_id) == {"A01", "A02", "A03"}
    assert df.groupby("astronaut_id").day.max().eq(14).all()
    a02 = df[df.astronaut_id == "A02"].iloc[-1]
    assert he.overall_level(a02) == 0


def test_baseline_flags_a_big_change():
    df = build_all()
    dev = deviations(df[df.astronaut_id == "A03"], window=5).set_index("field")
    assert dev.loc["sleep", "flag"]


def test_trend_and_hazard_scores():
    df = build_all()
    a1 = df[df.astronaut_id == "A01"]
    tr = trend_report(a1).set_index("indicator")
    assert tr.loc["sleep", "direction"] == "falling"
    hs = hazard_scores(a1)
    assert hs.score.between(0, 100).all() and len(hs) == 5


def test_db_roundtrip(tmp_path):
    db = DBManager(tmp_path / "t.db")
    db.seed(build_all())
    assert db.count("A01") == 14
    day = db.add_reading("A01", NORMAL)
    assert day == 15 and db.count("A01") == 15
    db.set_task("A01", day, "log", True)
    assert db.done_tasks("A01", day) == {"log"}
    db.set_task("A01", day, "log", False)
    assert db.done_tasks("A01", day) == set()
    db.reset("A01", build_all())
    assert db.count("A01") == 14
