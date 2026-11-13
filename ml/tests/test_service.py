
"""Tests for Vital Space prediction service."""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from risk import classify_review_priority, enrich_prediction
from service import predict_latest, serialize_prediction
from risk import assess_risk

class TestRiskClassification(unittest.TestCase):

    def test_anomaly_requires_review(self):
        self.assertEqual(
            classify_review_priority(True, "scored"),
            "review_required",
        )

    def test_normal_prediction(self):
        self.assertEqual(
            classify_review_priority(False, "scored"),
            "no_model_flag",
        )

    def test_insufficient_history(self):
        self.assertEqual(
            classify_review_priority(None, "insufficient_history"),
            "pending_history",
        )

    def test_prediction_enrichment(self):
        prediction = {
            "anomaly_detected": True,
            "model_status": "scored",
        }

        result = enrich_prediction(prediction)

        self.assertEqual(
            result["review_priority"],
            "review_required",
        )
        self.assertEqual(
            result["risk_assessment_status"],
            "not_clinically_validated",
        )


class TestPredictionService(unittest.TestCase):

    def test_prediction_serialization(self):
        row = pd.Series({
            "reading_id": "R0001",
            "astronaut_id": "AST001",
            "timestamp": "2026-11-01T08:00:00Z",
            "mission_day": 1,
            "anomaly_detected": pd.NA,
            "anomaly_score": float("nan"),
            "model_status": "insufficient_history",
        })

        result = serialize_prediction(row)

        self.assertIsNone(result["anomaly_detected"])
        self.assertIsNone(result["anomaly_score"])
        self.assertEqual(
            result["review_priority"],
            "pending_history",
        )


class TestRiskAssessment(unittest.TestCase):

    def test_low_risk(self):
        result = assess_risk(False, "scored")

        self.assertEqual(result["risk_level"], "low")
        self.assertEqual(result["risk_reasons"], [])

    def test_ml_anomaly(self):
        result = assess_risk(True, "scored")

        self.assertEqual(result["risk_level"], "moderate")
        self.assertIn(
            "ml_anomaly_detected",
            result["risk_reasons"],
        )

    def test_insufficient_history(self):
        result = assess_risk(
            None,
            "insufficient_history",
        )

        self.assertEqual(result["risk_level"], "unknown")

    def test_external_high_priority_signal(self):
        signals = [
            {
                "code": "demo_rule_001",
                "level": "high",
                "source": "synthetic_test",
            }
        ]

        result = assess_risk(
            False,
            "scored",
            signals=signals,
        )

        self.assertEqual(result["risk_level"], "high")
        self.assertIn(
            "demo_rule_001",
            result["risk_reasons"],
        )

    def test_invalid_signal(self):
        signals = [
            {
                "code": "invalid",
                "level": "critical",
                "source": "synthetic_test",
            }
        ]

        with self.assertRaises(ValueError):
            assess_risk(False, "scored", signals)


if __name__ == "__main__":
    unittest.main()
