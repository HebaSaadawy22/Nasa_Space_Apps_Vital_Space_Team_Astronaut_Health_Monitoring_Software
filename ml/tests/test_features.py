import sys
from pathlib import Path
import unittest
import pandas as pd
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features import build_features

class TestFeatures(unittest.TestCase):
    def test_no_future_reading_leakage(self):
        raw = pd.read_csv(ROOT / "data/astronaut_kafka_raw.csv")
        original = build_features(raw)
        changed = raw.copy()
        idx = changed.index[(changed.astronaut_id == "AST001") & (changed.mission_day == 30)][0]
        changed.loc[idx, "heart_rate"] = 200
        rerun = build_features(changed)
        before = original[(original.astronaut_id == "AST001") & (original.mission_day < 30)]
        after = rerun[(rerun.astronaut_id == "AST001") & (rerun.mission_day < 30)]
        np.testing.assert_allclose(before.hr_rolling_3d, after.hr_rolling_3d, equal_nan=True)
    def test_first_three_readings_need_history(self):
        result = build_features(pd.read_csv(ROOT / "data/astronaut_kafka_raw.csv"))
        self.assertTrue(result[result.mission_day <= 3].hr_rolling_3d.isna().all())
        self.assertTrue(result[result.mission_day >= 4].hr_rolling_3d.notna().all())

if __name__ == "__main__":
    unittest.main()
