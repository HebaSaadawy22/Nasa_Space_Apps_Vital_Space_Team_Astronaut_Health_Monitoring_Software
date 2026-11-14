"""Exploratory model inference. No medical diagnosis or certified spacecraft alerting."""
import json
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MODEL_PATHS = {
    'environment': HERE / 'nasa_iss_isolation_forest.joblib',
    'health_population': HERE / 'nhanes_isolation_forest.joblib',
}

class InferenceService:
    def __init__(self, paths=None):
        self.paths = paths or MODEL_PATHS
        self.bundles = {key: joblib.load(path) for key, path in self.paths.items()}

    def predict(self, message):
        if not isinstance(message, dict):
            raise ValueError('Message must be a JSON object')
        kind = message.get('source')
        if kind not in self.bundles:
            raise ValueError("source must be 'environment' or 'health_population'")
        b = self.bundles[kind]
        features = b['features']
        missing = [k for k in features if k not in message]
        if missing:
            raise ValueError(f'Missing required measurements: {missing}')
        try:
            values = [float(message[k]) for k in features]
        except (TypeError, ValueError) as err:
            raise ValueError('All measurements must be numeric') from err
        if not all(np.isfinite(values)):
            raise ValueError('All measurements must be finite')
        row = pd.DataFrame([values], columns=features)
        # NASA: decision_function score below custom training threshold => flagged
        # NHANES: negative decision_function score => flagged
        decision = float(b['pipeline'].decision_function(row)[0])
        threshold = float(b['threshold']) if kind == 'environment' else 0.0
        flagged = decision < threshold
        return {
            'source': kind,
            'timestamp': message.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            'entity_id': str(message.get('entity_id', 'unknown')),
            'is_anomaly': bool(flagged),
            'anomaly_score': round(float(threshold - decision), 6),
            'score_rule': 'positive = statistically unusual relative to model threshold',
            'features': dict(zip(features, values)),
            'interpretation': ('Unusual ISS environmental telemetry' if kind == 'environment'
                               else 'Cross-sectional population outlier; NOT individual health deterioration'),
            'status': 'review' if flagged else 'typical',
            'clinical_or_safety_alert': False,
        }
