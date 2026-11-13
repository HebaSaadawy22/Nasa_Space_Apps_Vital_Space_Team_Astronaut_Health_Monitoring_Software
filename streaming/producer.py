"""Sensor simulator: replays the raw CSV to Kafka in chronological order.

Only RAW measurements are sent (never the rolling features).

    python -m streaming.producer --delay 0.5            # one message every 0.5 s
    python -m streaming.producer --delay 0 --loops 1    # as fast as possible
    python -m streaming.producer --inject-bad 0.1       # 10% corrupted readings (tests validation)
"""
from __future__ import annotations

import argparse
import json
import random
import time

import pandas as pd
from confluent_kafka import Producer

from . import config


def load_readings(path) -> list[dict]:
    df = pd.read_csv(path)
    df["_ts"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["_ts", "astronaut_id"]).drop(columns="_ts")
    return df[config.RAW_FIELDS].to_dict("records")


def corrupt(r: dict) -> dict:
    r = dict(r)
    kind = random.choice(["hr", "bp", "missing", "ts"])
    if kind == "hr":
        r["heart_rate"] = 999
    elif kind == "bp":
        r["systolic_bp"], r["diastolic_bp"] = r["diastolic_bp"], r["systolic_bp"]
    elif kind == "missing":
        r["spo2"] = None
    else:
        r["timestamp"] = "not-a-date"
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between messages")
    ap.add_argument("--loops", type=int, default=1, help="how many times to replay the file")
    ap.add_argument("--inject-bad", type=float, default=0.0, help="fraction of corrupted readings")
    args = ap.parse_args()

    producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP, "enable.idempotence": True})
    readings = load_readings(config.RAW_CSV)
    print(f"Loaded {len(readings)} readings -> topic '{config.TOPIC_RAW}'")

    def on_delivery(err, msg):
        if err:
            print(f"Delivery failed: {err}")

    sent = 0
    for loop in range(args.loops):
        for r in readings:
            if random.random() < args.inject_bad:
                r = corrupt(r)
            # key = astronaut_id -> same astronaut always lands in the same partition (keeps order)
            producer.produce(
                config.TOPIC_RAW,
                key=str(r["astronaut_id"]),
                value=json.dumps(r, default=str),
                on_delivery=on_delivery,
            )
            producer.poll(0)
            sent += 1
            if args.delay:
                time.sleep(args.delay)
        print(f"Loop {loop + 1}/{args.loops} done ({sent} sent)")
    producer.flush()
    print("Finished.")


if __name__ == "__main__":
    main()
