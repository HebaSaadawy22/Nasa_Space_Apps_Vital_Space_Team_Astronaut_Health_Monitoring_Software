"""Vital Space: crew health self-assessment. Run with `streamlit run app.py`."""
import streamlit as st

from src.analysis import health_engine as he
from src.data.data_loader import get_readings
from src.utils import ui
from src.utils.constants import ENVIRONMENTS

astro, env = ui.page("Home", "🚀")

st.title("Vital Space")
st.caption("Crew health self-assessment for long-duration missions · NASA Space Apps Challenge 2026")

df = get_readings(astro["id"])
latest = df.iloc[-1]
b = he.banner(latest, env)

c1, c2, c3 = st.columns(3)
c1.metric("Crew member", astro["name"])
c2.metric("Mission day", int(latest["day"]))
c3.metric("Contact with Earth", ENVIRONMENTS[env]["delay"])

ui.banner(b["level"], b["title"], b["text"])

st.subheader("What this tool does")
st.write(
    "Astronauts carry much of the responsibility for spotting health changes in themselves on long missions. "
    "Vital Space collects daily health indicators, colors them by status, compares them with the crew member's own baseline, "
    "links them to the five spaceflight hazards, and tells the crew what to do and when to escalate to the flight surgeon."
)

cols = st.columns(3)
cards = [
    ("Health Dashboard", "Today's indicators, guidance and the daily log form."),
    ("Health Analytics", "Trends, personal baseline and projected range exits."),
    ("Interactive Body", "Click a body system to see how spaceflight affects it."),
    ("Space Hazards", "The five NASA hazards with a live risk score."),
    ("Daily Routine", "Health tasks with points and a streak."),
    ("Health Assistant", "Ask a question and get rule-based guidance."),
]
for i, (t, d) in enumerate(cards):
    with cols[i % 3]:
        st.markdown(f'<div class="vs-card"><strong>{t}</strong><p>{d}</p></div>', unsafe_allow_html=True)

if df["is_example"].any():
    st.info("Days with example data are simulated. Add your own readings on the Health Dashboard page.")
