import streamlit as st

from src.analysis import health_engine as he
from src.data.data_loader import get_db, get_readings, reset_astronaut
from src.utils import ui
from src.utils.constants import FIELDS, INDICATORS, LEVEL_NAMES, MOODS, ORDER

astro, env = ui.page("Health Dashboard", "🩺")
st.title("Health Dashboard")

df = get_readings(astro["id"])
latest = df.iloc[-1]
b = he.banner(latest, env)
ui.banner(b["level"], b["title"], b["text"])
st.caption(f'{astro["name"]} · mission day {int(latest["day"])}')

# indicator tiles
ev = he.evaluate(latest)
cols = st.columns(4)
for i, ind in enumerate(INDICATORS):
    e = ev[ind["id"]]
    with cols[i % 4]:
        st.markdown(
            f'<div class="vs-tile vs-l{e["level"]}"><div class="nm">{e["name"]}</div>'
            f'<div class="val">{e["value"]}<small>{e["unit"]}</small></div>{ui.badge(e["level"])}</div>',
            unsafe_allow_html=True,
        )

# guidance
st.subheader("Guidance")
names = {i["id"]: i["name"] for i in INDICATORS}
default = next((i["id"] for i in INDICATORS if ev[i["id"]]["level"] > 0), "hr")
pick = st.selectbox("Indicator", list(names), index=list(names).index(default), format_func=names.get)
lvl = ev[pick]["level"]
g = he.guidance(pick, lvl, env)
left, right = st.columns([1, 1])
with left:
    st.markdown(f"{ui.badge(lvl)} &nbsp; **{ev[pick]['value']} {ev[pick]['unit']}**", unsafe_allow_html=True)
    if g["note"]:
        st.markdown(f'<div class="vs-esc vs-l{lvl}"><strong>{"Escalate now." if lvl == 2 else "Flag it."}</strong> {g["note"]}</div>', unsafe_allow_html=True)
    st.markdown("**What to do now**" if lvl else "**Status**")
    for a in g["actions"]:
        st.markdown(f"- {a}")
with right:
    st.markdown("**Why it matters in space**")
    st.write(g["why"])
    st.markdown("**How to measure**")
    st.write(g["how"])

# log form
st.subheader("Log today's readings")
st.caption(f"Saving adds mission day {int(latest['day']) + 1}.")
with st.form("log"):
    cols = st.columns(3)
    vals = {}
    for i, k in enumerate(ORDER):
        f = FIELDS[k]
        with cols[i % 3]:
            label = f'{f["label"]} ({f["unit"]})'
            if k == "mood":
                vals[k] = st.selectbox(label, [5, 4, 3, 2, 1], index=[5, 4, 3, 2, 1].index(int(latest[k])), format_func=lambda n: f"{n} · {MOODS[n]}")
            elif f["dec"] == 0:
                vals[k] = st.number_input(label, int(f["min"]), int(f["max"]), int(latest[k]), step=int(f["step"]))
            else:
                vals[k] = st.number_input(label, float(f["min"]), float(f["max"]), float(latest[k]), step=float(f["step"]), format=f"%.{f['dec']}f")
    if st.form_submit_button("Save readings", type="primary"):
        day = get_db().add_reading(astro["id"], vals)
        get_db().set_task(astro["id"], day, "log", True)
        n = sum(1 for v in he.evaluate(vals).values() if v["level"] > 0)
        st.success(f"Day {day} saved. " + (f"{n} indicator(s) outside the normal range." if n else "All indicators normal."))
        st.rerun()

if st.button("Reset example data for this crew member"):
    reset_astronaut(astro["id"])
    st.rerun()
