
"""End-to-end tests for Vital Space ML inference."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from health_rules import HealthRule
from service import predict_readings
from streaming import StreamingPredictor


DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"

OUTPUT_FIELDS = (
    "reading_id",
    "astronaut_id",
    "mission_day",
    "anomaly_detected",
    "model_status",
    "risk_level",
    "risk_reasons",
    "review_priority",
    "risk_scope",
    "risk_assessment_status",
)


class TestEndToEnd(unittest.TestCase):
    """Verify batch and streaming inference consistency."""

    @classmethod
    def setUpClass(cls):
        raw = pd.read_csv(DATA_PATH)

        cls.raw = raw.loc[
            raw["mission_day"].between(1, 5)
            & raw["astronaut_id"].isin(
                ["AST001", "AST002"]
            )
        ].copy()

        cls.raw = cls.raw.sort_values(
            ["timestamp", "astronaut_id"]
        ).reset_index(drop=True)

        cls.demo_rule = HealthRule(
            code="demo_activity_review",
            metric="activity_minutes",
            operator="ge",
            threshold=0,
            level="moderate",
            source="synthetic_test_only",
        )

    def run_streaming(self, rules=()):
        """Process readings with isolated persistent state."""
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "test_state.sqlite3"

            with StreamingPredictor(
                state_path=state_path,
                rules=rules,
            ) as predictor:
                return [
                    predictor.process(reading)
                    for reading in self.raw.to_dict("records")
                ]

    def assert_predictions_equal(self, batch, streaming):
        """Compare complete inference outputs."""
        batch_by_id = {
            item["reading_id"]: item for item in batch
        }

        self.assertEqual(len(batch), len(streaming))

        for actual in streaming:
            expected = batch_by_id[actual["reading_id"]]

            for field in OUTPUT_FIELDS:
                self.assertEqual(
                    actual[field],
                    expected[field],
                    msg=f"Mismatch in {field}",
                )

            if expected["anomaly_score"] is None:
                self.assertIsNone(actual["anomaly_score"])
            else:
                self.assertAlmostEqual(
                    actual["anomaly_score"],
                    expected["anomaly_score"],
                    places=9,
                )

            self.assertEqual(
                pd.Timestamp(actual["timestamp"]),
                pd.Timestamp(expected["timestamp"]),
            )

    def test_batch_streaming_without_rules(self):
        batch = predict_readings(self.raw)
        streaming = self.run_streaming()

        self.assert_predictions_equal(batch, streaming)

    def test_batch_streaming_with_rules(self):
        rules = (self.demo_rule,)

        batch = predict_readings(self.raw, rules=rules)
        streaming = self.run_streaming(rules=rules)

        self.assert_predictions_equal(batch, streaming)

    def test_rules_work_without_model_history(self):
        results = predict_readings(
            self.raw,
            rules=(self.demo_rule,),
        )

        first_day = [
            item for item in results
            if item["mission_day"] == 1
        ]

        self.assertEqual(len(first_day), 2)

        for result in first_day:
            self.assertEqual(
                result["model_status"],
                "insufficient_history",
            )
            self.assertEqual(
                result["risk_level"],
                "moderate",
            )
            self.assertIsNone(
                result["anomaly_detected"]
            )
            self.assertIn(
                "demo_activity_review",
                result["risk_reasons"],
            )

    def test_rules_disabled_by_default(self):
        results = predict_readings(self.raw)

        self.assertTrue(
            all(
                "demo_activity_review"
                not in item["risk_reasons"]
                for item in results
            )
        )

    def test_results_are_not_clinically_validated(self):
        results = predict_readings(
            self.raw,
            rules=(self.demo_rule,),
        )

        for result in results:
            self.assertEqual(
                result["risk_assessment_status"],
                "not_clinically_validated",
            )


if __name__ == "__main__":
    unittest.main()
