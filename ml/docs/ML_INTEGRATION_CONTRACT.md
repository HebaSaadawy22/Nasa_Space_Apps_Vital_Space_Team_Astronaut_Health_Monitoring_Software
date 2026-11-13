# Vital Space — ML Integration Contract

**Version:** 1.0 — Experimental  
**Component:** Astronaut Health Anomaly Detection and Review Assessment

## 1. Purpose

The ML component processes astronaut health readings, detects statistical anomalies, and produces operational review-priority assessments.

This component does not provide medical diagnoses or clinically validated risk predictions.

## 2. Input

The integration accepts one raw astronaut reading as a Python dictionary containing the fields defined in `data_dictionary.csv`.

Required fields include:

- Identification: `reading_id`, `astronaut_id`
- Timing: `timestamp`, `mission_day`
- Vital signs: `heart_rate`, `systolic_bp`, `diastolic_bp`, `blood_glucose`, `body_temperature`, `spo2`
- Context: `glucose_context`, `sleep_hours`, `mood_score`, `activity_minutes`
- Environment: `cabin_co2_ppm`, `cabin_temp_c`, `cabin_humidity_pct`, `radiation_dose_rate_uSv_h`
- Provenance: `data_source`

The complete required input schema is defined in `src/validation.py`.

Timestamps must be timezone-aware and expressed in UTC.

## 3. Streaming Interface

```python
from streaming import StreamingPredictor

with StreamingPredictor() as predictor:
    result = predictor.process(message)
```

The predictor maintains astronaut-specific history using local SQLite state.

Each astronaut must have three valid preceding readings before the initial ML score can be generated.

## 4. Output Schema

| Field | Type | Description |
|---|---|---|
| reading_id | string | Original reading ID |
| astronaut_id | string | Astronaut identifier |
| timestamp | string | UTC measurement timestamp |
| mission_day | integer | Mission day |
| anomaly_detected | boolean or null | ML anomaly decision |
| anomaly_score | float or null | Higher values indicate greater statistical anomaly |
| model_status | string | scored or insufficient_history |
| risk_level | string | low, moderate, high, or unknown |
| risk_reasons | array of strings | Reasons for review classification |
| review_priority | string | Operational review decision |
| risk_scope | string | Experimental classification scope |
| risk_assessment_status | string | Clinical validation disclaimer |

## 5. Rules and Model Behavior

- The model uses the feature names and order stored in the trained model bundle.
- Rolling features use previous readings from the same astronaut only.
- ML anomaly detection and health-rule signals are separate mechanisms.
- Health rules are optional and must be explicitly configured.
- A low review level does not establish medical safety.
- Health-rule thresholds require suitable scientific review before operational use.

## 6. Message Processing Requirements

- Process readings chronologically within each astronaut.
- Use `astronaut_id` as the logical per-astronaut stream key.
- Duplicate reading IDs are currently rejected.
- Late readings are currently rejected.
- Do not automatically retry permanently invalid messages indefinitely.
- Do not send precomputed rolling features in raw sensor messages.

The current local implementation does not provide Kafka offset management, exactly-once delivery, distributed concurrency guarantees, or persistent prediction-result idempotency.

These responsibilities must be resolved during integration.

## 7. Model Limitations

Training data are synthetic demonstration data and do not represent real NASA astronaut medical records.

The model has not been clinically validated. There are no ground-truth clinical anomaly labels, and the reported experiments cannot establish medical sensitivity, specificity, or diagnostic accuracy.

**Integration status:** Local Python interface available. Kafka integration pending.