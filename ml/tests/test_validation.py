
"""Unit tests for raw astronaut data validation."""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from validation import DataValidationError, validate_raw_readings
from service import predict_readings


DATA_PATH = ROOT_DIR / "data" / "astronaut_kafka_raw.csv"


class TestDataValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sample = pd.read_csv(DATA_PATH).head(4)

    def setUp(self):
        self.data = self.sample.copy()

    def test_valid_readings(self):
        result = validate_raw_readings(self.data)
        self.assertEqual(len(result), 4)

    def test_missing_column(self):
        invalid = self.data.drop(columns=["heart_rate"])

        with self.assertRaises(DataValidationError):
            validate_raw_readings(invalid)

    def test_missing_value(self):
        self.data.loc[0, "spo2"] = None

        with self.assertRaises(DataValidationError):
            validate_raw_readings(self.data)

    def test_invalid_oxygen_range(self):
        self.data.loc[0, "spo2"] = 110

        with self.assertRaises(DataValidationError):
            validate_raw_readings(self.data)

    def test_duplicate_reading_id(self):
        self.data.loc[1, "reading_id"] = self.data.loc[
            0, "reading_id"
        ]

        with self.assertRaises(DataValidationError):
            validate_raw_readings(self.data)

    def test_invalid_timestamp(self):
        self.data.loc[0, "timestamp"] = "invalid-date"

        with self.assertRaises(DataValidationError):
            validate_raw_readings(self.data)

    def test_missing_timezone(self):
        self.data.loc[0, "timestamp"] = "2026-11-01T08:00:00"

        with self.assertRaises(DataValidationError):
            validate_raw_readings(self.data)

    def test_chronological_order(self):
        shuffled = self.data.iloc[::-1].copy()
        result = validate_raw_readings(shuffled)

        self.assertTrue(
            result["timestamp"].is_monotonic_increasing
        )

    def test_late_reading(self):
        last_seen = {
            "AST001": "2026-11-02T08:00:00Z"
        }

        with self.assertRaises(DataValidationError):
            validate_raw_readings(
                self.data,
                last_seen=last_seen,
            )

    def test_service_rejects_invalid_data(self):
        self.data.loc[0, "spo2"] = 120

        with self.assertRaises(DataValidationError):
            predict_readings(self.data)

    def test_original_data_unchanged(self):
        original = self.data.copy(deep=True)

        validate_raw_readings(self.data)

        pd.testing.assert_frame_equal(self.data, original)


if __name__ == "__main__":
    unittest.main()
