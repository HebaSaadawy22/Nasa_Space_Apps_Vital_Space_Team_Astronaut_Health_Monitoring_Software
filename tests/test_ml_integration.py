import pytest

from streaming import config

pytestmark = pytest.mark.skipif(not (config.ML_DIR / "src" / "streaming.py").exists(), reason="ml/ folder not present")


def test_ml_scores_every_ready_reading(tmp_path, monkeypatch):
    from streaming import consumer
    from streaming.ml_adapter import load_predictor
    from streaming.producer import load_readings

    monkeypatch.setattr(config, "ML_STATE_PATH", tmp_path / "state.sqlite3")
    monkeypatch.setattr(consumer, "ML", load_predictor(reset=True))
    p = consumer.Pipeline()
    scored = warm = 0
    for raw in load_readings(config.RAW_CSV):
        status, rec = p.run(raw)
        assert status == "ok"
        pred = rec["prediction"]
        assert pred["model_status"] != "error", pred
        if pred["model_status"] == "scored":
            scored += 1
            assert isinstance(pred["anomaly_detected"], bool) and rec["ml_ready"]
        else:
            warm += 1
            assert not rec["ml_ready"]
    assert (scored, warm) == (162, 18)
