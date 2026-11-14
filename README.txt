
ASTRONAUT HEALTH MONITORING — REAL DATA HANDOFF

DATA SOURCES:

1. NASA RR-1
   Environmental measurements: cabin temperature,
   humidity, CO2, radiation.
   39 daily records.
   Radiation unit: mGy/day.

2. BIDMC / PhysioNet
   Hospital patient HR and SpO2 recordings.
   1430 records from 3 recordings.
   time_seconds is relative to each recording.

3. NHANES 2017-2018
   Population survey: blood pressure, fasting
   glucose, usual weekday sleep, activity.
   2371 complete-case participants.
   These are NOT time-series records.

4. WESAD S2
   Wearable measurements: skin temperature,
   EDA and heart rate.
   7864 aligned 1-second records.

IMPORTANT:
- These datasets represent DIFFERENT subjects
  and different collection periods.
- Do not join them by row number or fabricate
  simultaneous measurements.
- They do not represent astronaut medical data.
- WESAD EDA is not a confirmed stress label.
- No clinical anomaly labels are provided here.
- Keep the synthetic astronaut dataset separate
  for end-to-end pipeline testing.
