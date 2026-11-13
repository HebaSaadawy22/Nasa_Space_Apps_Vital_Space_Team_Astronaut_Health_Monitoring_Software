import pandas as pd

from streaming import config
from streaming.consumer import Pipeline
from streaming.producer import load_readings
from streaming.validation import validate_reading


def test_pipeline_matches_notebook_ml_ready_csv():
    """Streaming features must equal the notebook's astronaut_ml_ready.csv."""
    p = Pipeline()
    rows = []
    for raw in load_readings(config.RAW_CSV):
        status, rec = p.run(raw)
        assert status == "ok"
        if rec["ml_ready"]:
            rows.append(rec)
    got = pd.DataFrame(rows).set_index("reading_id")
    exp = pd.read_csv(config.ROOT / "astronaut_ml_ready.csv").set_index("reading_id")
    assert set(got.index) == set(exp.index)
    cols = config.ML_FEATURES
    pd.testing.assert_frame_equal(got.loc[exp.index, cols].astype(float), exp[cols].astype(float), check_exact=False, rtol=1e-6)


def test_invalid_readings_are_rejected():
    good = load_readings(config.RAW_CSV)[0]
    assert validate_reading(good) == []
    assert validate_reading({**good, "heart_rate": 999})
    assert validate_reading({**good, "systolic_bp": 60, "diastolic_bp": 80})
    assert validate_reading({**good, "spo2": None})
    assert validate_reading({**good, "timestamp": "nope"})


def test_duplicate_reading_rejected():
    p = Pipeline()
    r = load_readings(config.RAW_CSV)[0]
    assert p.run(r)[0] == "ok"
    assert p.run(r)[0] == "invalid"
