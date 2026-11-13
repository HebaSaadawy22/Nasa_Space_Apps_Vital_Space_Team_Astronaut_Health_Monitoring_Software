import streamlit as st

from src.data.data_loader import get_db, get_readings
from src.utils import ui
from src.utils.constants import TASKS

astro, env = ui.page("Daily Routine", "✅")
st.title("Daily health routine")

db = get_db()
day = int(get_readings(astro["id"]).iloc[-1]["day"])
done = db.done_tasks(astro["id"], day)
st.caption(f"{astro['name']} · mission day {day}")

for t in TASKS:
    checked = st.checkbox(f"{t['label']}  (+{t['points']})", value=t["id"] in done, key=f"task-{astro['id']}-{day}-{t['id']}")
    if checked != (t["id"] in done):
        db.set_task(astro["id"], day, t["id"], checked)
        st.rerun()

done = db.done_tasks(astro["id"], day)
pts = sum(t["points"] for t in TASKS if t["id"] in done)
st.progress(pts / 100, text=f"Readiness {pts} / 100")
st.write(
    "Mission ready. Every health task is done." if pts >= 100 else
    "Strong day. Finish the last tasks." if pts >= 80 else
    "Steady. Keep going." if pts >= 50 else
    "Early in the day. Start with your readings."
)
streak = db.streak(astro["id"], {t["id"]: t["points"] for t in TASKS})
st.metric("Streak (days with 80+ points)", streak)
st.caption("Saving a reading on the Health Dashboard completes the first task and starts the next mission day.")
