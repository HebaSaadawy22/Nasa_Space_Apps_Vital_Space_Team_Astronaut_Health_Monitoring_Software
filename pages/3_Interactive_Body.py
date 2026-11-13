import plotly.graph_objects as go
import streamlit as st

from src.analysis import health_engine as he
from src.data.data_loader import get_readings
from src.utils import ui
from src.utils.constants import INDICATORS, LEVEL_COLORS, SYSTEMS

astro, env = ui.page("Interactive Body", "🧍")
st.title("Interactive Body")
st.caption("Click a marker on the body, or use the selector, to see how spaceflight affects that system.")

latest = get_readings(astro["id"]).iloc[-1]
levels = {k: he.system_level(k, latest) for k in SYSTEMS}
keys = list(SYSTEMS)

fig = go.Figure()
# simple silhouette
fig.add_shape(type="circle", x0=40, x1=60, y0=170, y1=190, line=dict(color="gray"), fillcolor="rgba(128,128,128,0.15)")
fig.add_shape(type="rect", x0=30, x1=70, y0=100, y1=168, line=dict(color="gray"), fillcolor="rgba(128,128,128,0.15)", layer="below")
fig.add_shape(type="rect", x0=12, x1=28, y0=104, y1=160, line=dict(color="gray"), fillcolor="rgba(128,128,128,0.15)")
fig.add_shape(type="rect", x0=72, x1=88, y0=104, y1=160, line=dict(color="gray"), fillcolor="rgba(128,128,128,0.15)")
fig.add_shape(type="rect", x0=34, x1=48, y0=5, y1=98, line=dict(color="gray"), fillcolor="rgba(128,128,128,0.15)")
fig.add_shape(type="rect", x0=52, x1=66, y0=5, y1=98, line=dict(color="gray"), fillcolor="rgba(128,128,128,0.15)")
fig.add_trace(go.Scatter(
    x=[SYSTEMS[k]["x"] for k in keys], y=[SYSTEMS[k]["y"] for k in keys], mode="markers+text",
    text=[SYSTEMS[k]["name"] for k in keys], textposition="middle right", customdata=keys,
    marker=dict(size=26, color=[LEVEL_COLORS[levels[k]] for k in keys], line=dict(width=2, color="white")),
    hovertemplate="%{text}<extra></extra>",
))
fig.update_xaxes(visible=False, range=[0, 130], fixedrange=True)
fig.update_yaxes(visible=False, range=[0, 200], fixedrange=True, scaleanchor="x", scaleratio=1)
fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, clickmode="event+select")

left, right = st.columns([1, 1])
with left:
    event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points", key="body")
clicked = None
try:
    pts = event.selection.points
    if pts:
        clicked = pts[0].get("customdata")
        clicked = clicked[0] if isinstance(clicked, (list, tuple)) else clicked
except Exception:
    clicked = None

with right:
    pick = st.selectbox("Body system", keys, index=keys.index(clicked) if clicked in keys else 0,
                        format_func=lambda k: SYSTEMS[k]["name"])
    s = SYSTEMS[pick]
    st.markdown(f"### {s['name']} &nbsp; {ui.badge(levels[pick])}", unsafe_allow_html=True)
    st.markdown("**Function**"); st.write(s["function"])
    st.markdown("**What spaceflight does**"); st.write(s["spaceflight"])
    st.markdown("**Countermeasure**"); st.write(s["countermeasure"])
    ev = he.evaluate(latest)
    linked = [i for i in INDICATORS if i["system"] == pick]
    st.markdown("**Linked indicators**")
    for i in linked:
        e = ev[i["id"]]
        st.markdown(f"- {i['name']}: **{e['value']} {e['unit']}** {ui.badge(e['level'])}", unsafe_allow_html=True)
