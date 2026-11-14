"""Demo replay of historic NASA CSV; simulates live delivery but is NOT live ISS data."""
import argparse
import json
import os
import time
import pandas as pd
from kafka import KafkaProducer


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default='RR-1_EDA_Telemetry_table(1).csv')
    p.add_argument('--delay', type=float, default=0.1)
    p.add_argument('--limit', type=int, default=50)
    args = p.parse_args()
    df = pd.read_csv(args.csv)
    df = df.sort_values('Controller_Time_GMT')
    producer = KafkaProducer(bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP', 'localhost:9092'),
                             value_serializer=lambda d: json.dumps(d).encode('utf-8'))
    for i, row in enumerate(df.head(args.limit).to_dict('records')):
        event = {'source': 'environment', 'entity_id': 'ISS',
                 'timestamp': str(row['Controller_Time_GMT']),
                 'Temp_degC_ISS': row['Temp_degC_ISS'],
                 'RH_percent_ISS': row['RH_percent_ISS'],
                 'CO2_ppm_ISS': row['CO2_ppm_ISS']}
        producer.send('astronaut.measurements', event).get(timeout=15)
        print('sent', i + 1, event['timestamp'])
        time.sleep(args.delay)
    producer.flush()

if __name__ == '__main__':
    main()
