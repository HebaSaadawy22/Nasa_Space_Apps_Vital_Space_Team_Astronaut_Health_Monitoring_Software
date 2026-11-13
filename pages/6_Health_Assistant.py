import streamlit as st

from src.analysis import health_engine as he
from src.data.data_loader import get_readings
from src.utils import ui
from src.utils.constants import ENVIRONMENTS, HAZARDS, INDICATORS, SYSTEMS

astro, env = ui.page("Health Assistant", "💬")
st.title("Health Assistant")
st.caption("Rule-based helper. It answers from the app's own reference content and your latest readings. It is not a doctor.")

latest = get_readings(astro["id"]).iloc[-1]
ev = he.evaluate(latest)

KEYWORDS = {
    "hr": ["heart rate", "pulse", "heartbeat", "bpm"],
    "bp": ["blood pressure", "pressure", "bp", "hypertension"],
    "glucose": ["glucose", "sugar", "diabetes"],
    "temp": ["temperature", "fever", "hot", "infection", "sick"],
    "sleep": ["sleep", "insomnia", "tired", "rest"],
    "mood": ["mood", "sad", "lonely", "stress", "anxious", "isolation"],
    "spo2": ["oxygen", "spo2", "breath", "co2", "headache"],
    "exercise": ["exercise", "bone", "muscle", "workout", "training"],
}


def answer(q: str) -> str:
    text = q.lower()
    if any(w in text for w in ["summary", "status", "how am i", "overall"]):
        b = he.banner(latest, env)
        lines = [f"**{b['title']}.** {b['text']}"]
        lines += [f"- {e['name']}: {e['value']} {e['unit']} ({['Normal', 'Watch', 'Alert'][e['level']]})" for e in ev.values()]
        return "\n".join(lines)
    for ind in INDICATORS:
        if any(w in text for w in KEYWORDS[ind["id"]]):
            e = ev[ind["id"]]
            g = he.guidance(ind["id"], e["level"], env)
            out = f"**{ind['name']}: {e['value']} {e['unit']} ({['Normal', 'Watch', 'Alert'][e['level']]})**\n\n"
            out += "\n".join(f"- {a}" for a in g["actions"])
            if g["note"]:
                out += f"\n\n{g['note']}"
            out += f"\n\n*Why it matters:* {g['why']}\n\n*How to measure:* {g['how']}"
            return out
    for h in HAZARDS:
        if any(w in text for w in h["name"].lower().split()[:1] + [h["id"]]):
            return f"**{h['name']}.** {h['text']} {h['action']}"
    for k, s in SYSTEMS.items():
        if k in text or s["name"].lower().split()[0] in text:
            return f"**{s['name']}.** {s['function']} {s['spaceflight']} {s['countermeasure']}"
    if any(w in text for w in ["doctor", "surgeon", "emergency", "help"]):
        return ENVIRONMENTS[env]["escalation"]
    return ("I can explain a health indicator (for example heart rate, sleep or glucose), a hazard, a body system, "
            "or give a summary of your status. Try: \"How am I doing?\" or \"Why is my sleep low?\"")


if "chat" not in st.session_state:
    st.session_state.chat = []
for who, msg in st.session_state.chat:
    st.chat_message(who).markdown(msg)

q = st.chat_input("Ask about your health, a hazard or a body system")
if q:
    st.session_state.chat.append(("user", q))
    st.session_state.chat.append(("assistant", answer(q)))
    st.rerun()
