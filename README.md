# Vital Space

Crew health self-assessment software for long-duration missions.
Built for the **NASA Space Apps Challenge 2026**: *Create Health Monitoring Software for Astronauts on Space Missions*.

Team: Vital Space

## What it does

Astronauts on long missions carry much of the responsibility for spotting health changes in themselves.
Vital Space collects daily health indicators, shows their status at a glance, compares them with the crew member's own baseline,
links them to NASA's five spaceflight hazards, and says what to do and when to escalate to the flight surgeon.

| Page | Purpose |
|---|---|
| Home | Crew status and overview |
| 1 Health Dashboard | Color-coded indicators, guidance, daily log form |
| 2 Health Analytics | Trend charts, personal baseline, projected range exits |
| 3 Interactive Body | Click a body system to see how spaceflight affects it |
| 4 Space Hazards | The five NASA hazards with a live risk score |
| 5 Daily Routine | Health tasks with points and a streak |
| 6 Health Assistant | Rule-based answers from the app's own reference content |

Indicators: heart rate, blood pressure, fasting glucose, temperature, sleep, mood, oxygen saturation, exercise minutes.
Environments: space station, lunar base, Mars transit (changes the escalation advice because of communication delay).

## Run it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Run the tests:

```bash
python -m pytest
```

Rebuild the example data:

```bash
python -m src.data.data_generator
```

## Project layout

```
app.py                 Home page
pages/                 Streamlit pages (one file per page)
src/utils/constants.py Reference ranges, indicators, body systems, hazards, tasks
src/analysis/          health_engine (rules), baseline, risk_assessment
src/database/          SQLite storage for readings and tasks
src/data/              data_loader, data_generator
data/                  sample_health_data.csv, astronauts.json (database is created on first run)
docs/                  architecture, user guide, scientific references
tests/                 unit tests
```

## Important notes

- Reference ranges are general adult values used for demonstration. They are **not medical advice**.
- Crew members and their readings are **simulated example data**.
- The Health Assistant is rule-based and does not use a language model.
