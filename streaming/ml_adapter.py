"""Loads the ML team's StreamingPredictor (ml/src/streaming.py) without clashing with this package's name."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from . import config

ML_SRC = config.ML_DIR / "src"


def load_predictor(reset: bool = False):
    """Return a StreamingPredictor. reset=True deletes its saved history (use when replaying from the start)."""
    entry = ML_SRC / "streaming.py"
    if not entry.exists():
        raise FileNotFoundError(f"{entry} not found. Get the ML folder: git checkout origin/feature/machine-learning -- ml")
    if str(ML_SRC) not in sys.path:
        sys.path.append(str(ML_SRC))  # the ML code uses flat imports (features, risk, validation, ...)
    spec = importlib.util.spec_from_file_location("ml_streaming", entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state = Path(config.ML_STATE_PATH)
    if reset and state.exists():
        state.unlink()
    return module.StreamingPredictor(state_path=state)
