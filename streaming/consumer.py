"""Python consumer: Kafka -> validate -> preprocess -> engineer features -> (ML model, next step).

    python -m streaming.consumer                 # run forever
    python -m streaming.consumer --from-beginning --max-messages 180

Valid readings go to the processed topic, invalid ones to the dead-letter topic with the reasons.
`handle_processed()` is the single hook where the ML model + PostgreSQL will plug in.
"""
from __future__ import annotations

import argparse
import json
import signal

from confluent_kafka import Consumer, KafkaError, Producer

from . import config
from .db import connect, init_schema, save
from .features import FeatureEngine
from .ml_adapter import load_predictor
from .risk import assess
from .validation import parse_timestamp, validate_reading

NUMERIC_INT = ["mission_day", "heart_rate", "systolic_bp", "diastolic_bp", "blood_glucose",
               "mood_score", "activity_minutes", "spo2", "cabin_co2_ppm"]
NUMERIC_FLOAT = ["body_temperature", "sleep_hours", "cabin_temp_c", "cabin_humidity_pct",
                 "radiation_dose_rate_uSv_h"]


def preprocess(r: dict) -> dict:
    """Cast types and normalize the timestamp to ISO 8601 UTC."""
    out = dict(r)
    for c in NUMERIC_INT:
        out[c] = int(float(r[c]))
    for c in NUMERIC_FLOAT:
        out[c] = float(r[c])
    out["timestamp"] = parse_timestamp(r["timestamp"]).isoformat()
    out["astronaut_id"] = str(r["astronaut_id"]).strip()
    return out


DB = None  # set in main() when PostgreSQL is available
ML = None  # set in main() when the ML model is available


def handle_processed(record: dict) -> dict:
    """Rule-based status, then save to PostgreSQL.

    """
    if ML is not None:
        try:
            record["prediction"] = ML.process({k: record[k] for k in config.RAW_FIELDS})
        except Exception as e:  # a model problem must never stop the stream
            record["prediction"] = {"model_status": "error", "error": str(e)}
    overall, alerts = assess(record)
    record["overall_level"] = overall
    record["alerts"] = alerts
    if DB is not None:
        save(DB, record, overall, alerts)
    return record


class Pipeline:
    """Kafka-independent processing core (easy to unit test)."""

    def __init__(self):
        self.engine = FeatureEngine()
        self.seen_ids: set[str] = set()

    def run(self, raw: dict) -> tuple[str, dict]:
        """Return ('ok', record) or ('invalid', {'reasons': [...], 'raw': raw})."""
        errors = validate_reading(raw)
        if errors:
            return "invalid", {"reasons": errors, "raw": raw}
        rec = preprocess(raw)
        if rec["reading_id"] in self.seen_ids:
            return "invalid", {"reasons": ["duplicate reading_id"], "raw": raw}
        if self.engine.is_stale(rec["astronaut_id"], rec["timestamp"]):
            return "invalid", {"reasons": ["out-of-order or duplicate timestamp"], "raw": raw}
        self.seen_ids.add(rec["reading_id"])
        return "ok", handle_processed(self.engine.process(rec))


def ml_tag(rec: dict) -> str:
    p = rec.get("prediction")
    if not p:
        return ""
    if p.get("model_status") == "scored":
        return f" ml={'ANOMALY' if p['anomaly_detected'] else 'normal'}({p['anomaly_score']:.2f}) risk={p.get('risk_level')}"
    return f" ml={p.get('model_status')}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-beginning", action="store_true")
    ap.add_argument("--max-messages", type=int, default=0, help="stop after N messages (0 = forever)")
    ap.add_argument("--no-db", action="store_true", help="do not save to PostgreSQL")
    ap.add_argument("--no-ml", action="store_true", help="do not run the ML model")
    args = ap.parse_args()

    group = config.CONSUMER_GROUP + ("-replay" if args.from_beginning else "")
    consumer = Consumer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP,
        "group.id": group,
        "auto.offset.reset": "earliest" if args.from_beginning else "latest",
        "enable.auto.commit": False,
    })
    out = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP})
    consumer.subscribe([config.TOPIC_RAW])

    running = True
    signal.signal(signal.SIGINT, lambda *_: globals().update(_stop=True))
    global DB, ML
    if not args.no_ml:
        try:
            ML = load_predictor(reset=args.from_beginning)
            print("ML model loaded: anomaly detection enabled")
        except Exception as e:
            print(f"WARNING: ML model unavailable ({e}); running without predictions")
    if not args.no_db:
        try:
            DB = connect()
            init_schema(DB)
            print("PostgreSQL connected: saving readings and alerts")
        except Exception as e:  # keep streaming even if the DB is down
            print(f"WARNING: PostgreSQL unavailable ({e}); running without saving")
    pipeline, counts, total = Pipeline(), {"ok": 0, "invalid": 0}, 0
    print(f"Consuming '{config.TOPIC_RAW}' (group={group}) ... Ctrl+C to stop")

    try:
        while running and not globals().get("_stop"):
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"Kafka error: {msg.error()}")
                continue
            try:
                raw = json.loads(msg.value())
                status, payload = pipeline.run(raw)
            except json.JSONDecodeError:
                status, payload = "invalid", {"reasons": ["malformed JSON"], "raw": msg.value().decode(errors="replace")}

            if status == "ok":
                out.produce(config.TOPIC_PROCESSED, key=payload["astronaut_id"], value=json.dumps(payload))
                tag = "ML-READY" if payload["ml_ready"] else "warm-up"
                print(f"OK   {payload['reading_id']} {payload['astronaut_id']} day {payload['mission_day']} [{tag}] level={payload['overall_level']}{ml_tag(payload)}")
            else:
                out.produce(config.TOPIC_DEAD_LETTER, value=json.dumps(payload, default=str))
                print(f"BAD  {payload['raw'].get('reading_id') if isinstance(payload['raw'], dict) else '?'}: {'; '.join(payload['reasons'])}")

            out.poll(0)
            consumer.commit(msg, asynchronous=False)  # commit only after handling
            counts[status] += 1
            total += 1
            if args.max_messages and total >= args.max_messages:
                break
    finally:
        out.flush()
        consumer.close()
        print(f"Done. valid={counts['ok']} invalid={counts['invalid']}")


if __name__ == "__main__":
    main()
