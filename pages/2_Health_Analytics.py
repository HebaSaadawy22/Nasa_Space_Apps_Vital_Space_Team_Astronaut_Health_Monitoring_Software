import plotly.graph_objects as go
import streamlit as st

from src.analysis.baseline import deviations
from src.analysis.risk_assessment import trend_report
from src.data.data_loader import get_readings
from src.analysis.health_engine import level
from src.utils import ui
from src.utils.constants import FIELDS, INDICATORS, LEVEL_COLORS

astro, env = ui.page("Health Analytics", "📈")
st.title("Health Analytics")

df = get_readings(astro["id"])
names = {i["id"]: i for i in INDICATORS}
pick = st.selectbox("Indicator", list(names), format_func=lambda k: names[k]["name"])
ind = names[pick]
days = st.slider("Days shown", 5, max(6, len(df)), min(14, len(df)))
d = df.tail(days)

fig = go.Figure()
for n, k in enumerate(ind["fields"]):
    lo, hi = FIELDS[k]["ok"]
    top = max(float(d[k].max()), hi) if hi < 300 else float(d[k].max())
    fig.add_hrect(y0=lo, y1=min(hi, top * 1.05), fillcolor="#2fb26b", opacity=0.12, line_width=0)
    fig.add_trace(go.Scatter(
        x=d["day"], y=d[k], mode="lines+markers", name=FIELDS[k]["label"],
        line=dict(dash="solid" if n == 0 else "dash"),
        marker=dict(size=9, color=[LEVEL_COLORS[level(k, v)] for v in d[k]], line=dict(width=1, color="white")),
    ))
fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Mission day",
                  yaxis_title=ind["unit"], legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, width="stretch")
st.caption("Green band is the normal range. Marker color shows the status of each day.")

left, right = st.columns(2)
with left:
    st.subheader("Personal baseline")
    st.caption("Latest value against this crew member's first 5 days.")
    dev = deviations(df, window=5)
    show = dev[["label", "baseline", "latest", "change", "z", "flag"]].rename(
        columns={"label": "Indicator", "baseline": "Baseline", "latest": "Latest", "change": "Change", "z": "z-score", "flag": "Flagged"})
    st.dataframe(show, hide_index=True, width="stretch")
with right:
    st.subheader("Trend outlook")
    st.caption("Direction over the last 7 days and days until the normal range is left if the trend continues.")
    tr = trend_report(df)[["name", "direction", "days_to_leave_range"]].rename(
        columns={"name": "Indicator", "direction": "Trend", "days_to_leave_range": "Days to leave range"})
    st.dataframe(tr, hide_index=True, width="stretch")
