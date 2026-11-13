
"""Tests for incremental astronaut predictions."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from predict import predict_history
from streaming import StreamingPredictor


class TestStreamingPredictor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(
            ROOT / "data" / "astronaut_kafka_raw.csv"
        )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "state.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_batch_stream_equivalence(self):
        expected = predict_history(
            self.raw
        ).set_index("reading_id")

        ordered = self.raw.sort_values(
            ["timestamp", "astronaut_id"]
        )

        with StreamingPredictor(state_path=self.db) as model:
            for reading in ordered.to_dict("records"):
                result = model.process(reading)
                reference = expected.loc[result["reading_id"]]

                self.assertEqual(
                    result["model_status"],
                    reference["model_status"],
                )

                if result["model_status"] == "scored":
                    self.assertEqual(
                        result["anomaly_detected"],
                        bool(reference["anomaly_detected"]),
                    )
                    self.assertAlmostEqual(
                        result["anomaly_score"],
                        float(reference["anomaly_score"]),
                        places=9,
                    )

    def test_first_three_require_history(self):
        with StreamingPredictor(state_path=self.db) as model:
            statuses = [
                model.process(row)["model_status"]
                for row in self.raw.head(4).to_dict("records")
            ]

        self.assertEqual(
            statuses,
            ["insufficient_history"] * 3 + ["scored"],
        )

    def test_duplicate_reading_rejected(self):
        row = self.raw.iloc[0].to_dict()

        with StreamingPredictor(state_path=self.db) as model:
            model.process(row)

            with self.assertRaisesRegex(ValueError, "Duplicate"):
                model.process(row)

    def test_late_reading_rejected(self):
        first, second = self.raw.iloc[:2].to_dict("records")

        with StreamingPredictor(state_path=self.db) as model:
            model.process(second)

            with self.assertRaisesRegex(ValueError, "Late"):
                model.process(first)

    def test_state_survives_restart(self):
        rows = self.raw.iloc[:4].to_dict("records")

        with StreamingPredictor(state_path=self.db) as model:
            for row in rows[:3]:
                model.process(row)

        with StreamingPredictor(state_path=self.db) as model:
            result = model.process(rows[3])

        self.assertEqual(result["model_status"], "scored")


if __name__ == "__main__":
    unittest.main()
