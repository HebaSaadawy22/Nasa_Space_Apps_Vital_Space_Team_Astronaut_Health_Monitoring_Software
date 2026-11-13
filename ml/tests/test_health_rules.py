
"""Tests for the configurable health rules engine."""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from health_rules import HealthRule, evaluate_health_rules
from risk import assess_risk


class TestHealthRules(unittest.TestCase):

    def setUp(self):
        self.demo_rule = HealthRule(
            code="demo_activity_check",
            metric="activity_minutes",
            operator="gt",
            threshold=100,
            level="moderate",
            source="synthetic_test_only",
        )

    def test_triggered_rule(self):
        reading = {"activity_minutes": 120}

        signals = evaluate_health_rules(
            reading,
            [self.demo_rule],
        )

        self.assertEqual(len(signals), 1)
        self.assertEqual(
            signals[0]["code"],
            "demo_activity_check",
        )

    def test_rule_not_triggered(self):
        reading = {"activity_minutes": 30}

        signals = evaluate_health_rules(
            reading,
            [self.demo_rule],
        )

        self.assertEqual(signals, [])

    def test_empty_rules(self):
        signals = evaluate_health_rules(
            {"activity_minutes": 120},
        )

        self.assertEqual(signals, [])

    def test_invalid_metric(self):
        with self.assertRaises(ValueError):
            HealthRule(
                code="invalid",
                metric="unknown_metric",
                operator="gt",
                threshold=100,
                level="moderate",
                source="synthetic_test_only",
            )

    def test_missing_metric(self):
        with self.assertRaises(ValueError):
            evaluate_health_rules(
                {},
                [self.demo_rule],
            )

    def test_duplicate_rule_code(self):
        with self.assertRaises(ValueError):
            evaluate_health_rules(
                {"activity_minutes": 120},
                [self.demo_rule, self.demo_rule],
            )

    def test_rule_and_ml_integration(self):
        signals = evaluate_health_rules(
            {"activity_minutes": 120},
            [self.demo_rule],
        )

        result = assess_risk(
            anomaly_detected=False,
            model_status="scored",
            signals=signals,
        )

        self.assertEqual(result["risk_level"], "moderate")
        self.assertIn(
            "demo_activity_check",
            result["risk_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
