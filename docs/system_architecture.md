# System architecture

## Overview

```
Streamlit pages  ->  src/analysis  ->  src/utils/constants
       |                  ^
       v                  |
 src/data/data_loader -> src/database/db_manager (SQLite)
       ^
       |
 data/sample_health_data.csv, data/astronauts.json
```

## Layers

**Pages (`app.py`, `pages/`)**: Streamlit UI only. Each page calls `src.utils.ui.page()` first, which sets the layout,
loads `assets/styles.css`, and draws the sidebar (crew member and environment).

**Analysis (`src/analysis/`)**
- `health_engine.py`: classifies each measured field as Normal (0), Watch (1) or Alert (2), combines fields per indicator,
  per body system and overall, and builds guidance and the status banner. Alert text depends on the environment.
- `baseline.py`: mean and spread of the first days of a mission, then the z-score of the latest reading. A floor on the spread
  keeps flat baselines from producing huge scores.
- `risk_assessment.py`: 7-day least-squares trend per indicator, days until the normal range is left, and a 0 to 100 score per hazard
  (70 percent current status, 30 percent adverse trend).

**Data (`src/data/`, `src/database/`)**: `data_generator` makes simulated crew data with different drift profiles.
`db_manager` stores readings and completed tasks in SQLite (`data/vital_space.db`, created on first run and seeded from the CSV).

**Constants (`src/utils/constants.py`)**: one source for ranges, indicator text, body systems, hazards, environments and tasks.
Changing a range or a message happens here only.

## Design decisions

- Rules are explicit and testable instead of a black box, so a crew member can see why a value is flagged.
- Thresholds live in one file so a flight surgeon can review and change them.
- Environment (station, Moon, Mars) changes the escalation message because communication delay changes what is possible.
