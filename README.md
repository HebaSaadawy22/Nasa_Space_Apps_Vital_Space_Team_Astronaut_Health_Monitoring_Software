# Astronaut Health Monitoring - Data Package

## Data Source
Synthetic demonstration data.
NOT real NASA astronaut medical records.

## Files
- astronaut_kafka_raw.csv: 180 records, 19 columns.
- astronaut_ml_ready.csv: 162 records, 29 columns.
- data_preprocessing.ipynb: Data analysis and processing.
- data_dictionary.csv: Column definitions and units.

## Processing
- Missing-value and duplicate checks
- Technical range validation
- Timestamp conversion to UTC
- EDA and correlation analysis
- Astronaut-specific rolling features
- Personal baseline deviations

## Important
The first 3 days per astronaut have insufficient
history for 3-day rolling features. These records
remain in the raw dataset but are excluded from
the ML-ready dataset.

Rolling features use previous observations only.

## For Kafka Team
Send raw readings in chronological order.
Do not send precomputed rolling features as
if they were raw sensor measurements.

## For ML Team
Use a chronological train/test split.
Do not treat synthetic patterns as clinical truth.
Anomaly detection is not medical diagnosis.
