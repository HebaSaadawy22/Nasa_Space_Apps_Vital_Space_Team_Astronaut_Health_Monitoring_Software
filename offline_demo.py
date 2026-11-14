"""Test both trained models without Kafka using actual CSV rows."""
import csv
import json
from pathlib import Path
import pandas as pd
from ml_service import InferenceService

HERE = Path(__file__).resolve().parent
service = InferenceService()
records = []
for path, source, entity in [
    (HERE / 'RR-1_EDA_Telemetry_table(1).csv', 'environment', 'ISS'),
    (HERE / 'nhanes_health(1).csv', 'health_population', 'NHANES-participant'),
]:
    df = pd.read_csv(path)
    for _, row in df.head(50).iterrows():
        rec = {**row.to_dict(), 'source': source, 'entity_id': str(row.get('SEQN', entity))}
        if source == 'environment':
            rec['timestamp'] = str(row['Controller_Time_GMT'])
        records.append(service.predict(rec))
with (HERE / 'sample_dashboard_events.jsonl').open('w', encoding='utf-8') as out:
    for item in records:
        out.write(json.dumps(item, ensure_ascii=False) + '\n')
print('Demo completed:', len(records), 'events written to sample_dashboard_events.jsonl')
print('Anomalies by source:')
for source in ('environment', 'health_population'):
    events = [x for x in records if x['source'] == source]
    print(source, sum(x['is_anomaly'] for x in events), '/', len(events))
