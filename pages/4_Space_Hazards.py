import plotly.graph_objects as go
import streamlit as st

from src.analysis import health_engine as he
from src.analysis.risk_assessment import hazard_scores
from src.data.data_loader import get_readings
from src.utils import ui
from src.utils.constants import HAZARDS, INDICATOR_BY_ID

astro, env = ui.page("Space Hazards", "☄️")
st.title("The five spaceflight hazards")
st.caption("Based on NASA's Human Research Program hazard list. Score = current status (70%) plus adverse trend (30%).")

df = get_readings(astro["id"])
latest = df.iloc[-1]
scores = hazard_scores(df).set_index("hazard")["score"]

fig = go.Figure(go.Bar(x=[HAZARDS[i]["name"] for i in range(len(HAZARDS))],
                       y=[int(scores[h["id"]]) for h in HAZARDS], marker_color=[
                           "#2fb26b" if scores[h["id"]] < 25 else "#e09a1f" if scores[h["id"]] < 60 else "#e5534b" for h in HAZARDS]))
fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 100], title="Risk score"))
st.plotly_chart(fig, width="stretch")

cols = st.columns(3)
for i, h in enumerate(HAZARDS):
    with cols[i % 3]:
        chips = " ".join(
            ui.badge(he.indicator_level(x, latest), f"{INDICATOR_BY_ID[x]['name']}") for x in h["indicators"]
        )
        st.markdown(
            f'<div class="vs-card"><strong>{h["name"]}</strong> &nbsp; <span class="mono">{int(scores[h["id"]])}/100</span>'
            f'<p>{h["text"]}</p><p><b>Action:</b> {h["action"]}</p><div>{chips}</div></div>',
            unsafe_allow_html=True,
        )
