"""Kafka consumer; input topic astronaut.measurements; output astronaut.anomaly-results."""
import json
import os
from kafka import KafkaConsumer, KafkaProducer
from ml_service import InferenceService

BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP', 'localhost:9092')
IN_TOPIC = os.getenv('KAFKA_INPUT_TOPIC', 'astronaut.measurements')
OUT_TOPIC = os.getenv('KAFKA_OUTPUT_TOPIC', 'astronaut.anomaly-results')


def main():
    service = InferenceService()
    consumer = KafkaConsumer(IN_TOPIC, bootstrap_servers=BOOTSTRAP,
                             group_id='astronaut-ml-v1', auto_offset_reset='earliest',
                             enable_auto_commit=False,
                             value_deserializer=lambda b: json.loads(b.decode('utf-8')))
    producer = KafkaProducer(bootstrap_servers=BOOTSTRAP,
                             value_serializer=lambda d: json.dumps(d).encode('utf-8'))
    print('Listening on', IN_TOPIC, '->', OUT_TOPIC)
    for message in consumer:
        try:
            result = service.predict(message.value)
        except (ValueError, KeyError) as err:
            # Invalid measurements are NOT considered health/environment anomalies.
            result = {'status': 'invalid_input', 'error': str(err),
                      'source': message.value.get('source') if isinstance(message.value, dict) else None,
                      'clinical_or_safety_alert': False}
        producer.send(OUT_TOPIC, result).get(timeout=15)
        consumer.commit()  # Commit only after outgoing message acknowledged (at-least-once)
        print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
