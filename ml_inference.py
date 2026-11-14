from pathlib import Path
import joblib
import numpy as np
import pandas as pd


class AstronautAnomalyDetector:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = (
                Path(__file__).resolve().parent
                / "astronaut_anomaly_model.joblib"
            )

        package = joblib.load(model_path)

        self.model = package["model"]
        self.scaler = package["scaler"]
        self.features = package["features"]

    def predict(self, record):
        missing = [
            f for f in self.features
            if f not in record
        ]

        if missing:
            raise ValueError(
                f"Missing ML features: {missing}"
            )

        X = pd.DataFrame([{
            f: record[f] for f in self.features
        }])

        X = X.apply(pd.to_numeric, errors="raise")

        if not np.isfinite(
            X.to_numpy(dtype=float)
        ).all():
            raise ValueError("Invalid numeric values")

        X_scaled = self.scaler.transform(X)

        score = float(
            -self.model.score_samples(X_scaled)[0]
        )

        is_anomaly = int(
            self.model.predict(X_scaled)[0] == -1
        )

        return {
            "anomaly_score": round(score, 6),
            "is_anomaly": is_anomaly,
            "status": (
                "ANOMALY" if is_anomaly
                else "NORMAL"
            )
        }
