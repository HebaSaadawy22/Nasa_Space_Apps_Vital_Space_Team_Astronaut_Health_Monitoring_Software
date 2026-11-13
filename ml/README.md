# Vital Space: Machine Learning Starter (Offline)

The dataset is **synthetic** and contains no verified anomaly labels. This project is a **technical demonstration**, not a medical diagnostic or validated emergency alert system.

## Quick start (Windows / VS Code / Python 3.11+)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/train.py
python src/predict.py
```

On Linux/macOS, activate with `source .venv/bin/activate`.

## Included
- `data/astronaut_kafka_raw.csv`: 180 synthetic raw readings, 6 astronauts x 30 days
- `data/astronaut_ml_ready.csv`: 162 ready readings, 29 columns
- `src/features.py`: reproduces the notebook's history-only rolling and deviation recipe
- `src/train.py`: chronological split (mission days 4-23 train, 24-30 test); IsolationForest demo
- `src/predict.py`: reload and score raw history; first 3 per astronaut return `insufficient_history`
- `tests/test_features.py`: two guardrails for rolling-history correctness
- `artifacts/anomaly_model.joblib`: created after training
- `outputs/predictions.csv` and `outputs/summary.json`: created after training

## Kafka contract and limitations
Producer should send **raw fields only**. The consumer must keep at least the previous **three chronological readings per astronaut** (or query them from persistent storage), then compute derived features via exactly the same algorithm. `predict_history` rebuilds from a full batch of history for an offline integration test; it is **not a real-time Kafka consumer**. For days/readings with insufficient history, return `model_status=insufficient_history` with no anomaly prediction.

`anomaly_score = -decision_function()`: higher indicates greater anomaly relative to this **specific fitted model**; it is NOT a calibrated probability or medical risk percentage. `contamination=0.08` is an arbitrary baseline setting. Do not interpret flagged records as clinical truth, and do not claim accuracy/recall without reviewed labels. The holdout includes future days of the same synthetic astronauts; it does not measure generalization to new astronauts or real-world operations.

Future integration should have schema validation, duplicate detection, delayed/out-of-order event handling, per-astronaut state persistence, and model version tracking. Clinical rules and safety escalation must be maintained separately and assessed with domain experts.
