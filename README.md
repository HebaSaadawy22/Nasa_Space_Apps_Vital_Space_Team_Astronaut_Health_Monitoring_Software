# Astronaut ML — Isolation Forest Integration

Two **exploratory** anomaly-detection models:
- **NASA ISS environment:** temperature, humidity, CO₂.
- **NHANES population health:** blood pressure, glucose, sleep, activity.

NHANES identifies statistical outliers across different participants. Neither model
is validated for medical diagnosis or spacecraft safety decisions.

## Install
```bash
pip install -r requirements.txt
```

## Local offline test
Place the two source CSVs (not included in this repository) in this folder:
- `RR-1_EDA_Telemetry_table(1).csv`
- `nhanes_health(1).csv`

Then run:
```bash
python offline_demo.py
streamlit run dashboard.py
```

## Kafka integration
Start a Kafka broker on `localhost:9092` and create:
- `astronaut.measurements`
- `astronaut.anomaly-results`

Then, in separate terminals:
```bash
python consumer.py
python producer.py --csv "RR-1_EDA_Telemetry_table(1).csv" --limit 50 --delay 0.2
```

The consumer publishes anomaly results to `astronaut.anomaly-results`.
The included Streamlit dashboard reads a local **demo JSONL file** only; it is
not a live Kafka dashboard.

## Repository contents
- `ml_service.py`: inference for both models
- `consumer.py`: Kafka Consumer + results Producer
- `producer.py`: historical NASA CSV replay to Kafka
- `offline_demo.py`: offline scoring from your local CSVs
- `dashboard.py`: demonstration Streamlit UI
- `*.joblib`: serialized model artifacts
- `requirements.txt`: Python dependencies

## Important limitations
Never compare raw anomaly scores across the two models.
Use trained models only from trusted sources. NASA readings are historical;
NHANES rows represent different people, not an astronaut time series.
Do not automatically act on these experimental anomaly signals.
