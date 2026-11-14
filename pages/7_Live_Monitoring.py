"""Live monitoring page: reads the readings and alerts that the Kafka consumer saved to PostgreSQL."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.health_engine import level as lv
from src.utils import ui
from src.utils.constants import LEVEL_NAMES
from streaming import config
from streaming.db import connect
from streaming.risk import FIELD_MAP, assess
from src.utils.constants import FIELDS

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Live Monitoring · Vital Space", page_icon="📡", layout="wide")
_css = ROOT / "assets" / "styles.css"
if _css.exists():
    st.markdown(f"<style>{_css.read_text()}</style>", unsafe_allow_html=True)
_logo = ROOT / "assets" / "logo.png"
if _logo.exists():
    st.logo(str(_logo))
st.title("Live Monitoring")
st.caption("Data flows Sensors → Kafka → Python Consumer → PostgreSQL → this page. Synthetic demonstration data.")

METRICS = {"heart_rate": "Heart rate (bpm)", "spo2": "SpO₂ (%)", "systolic_bp": "Systolic BP (mmHg)",
           "blood_glucose": "Glucose (mg/dL)", "body_temperature": "Temperature (°C)",
           "sleep_hours": "Sleep (h)", "mood_score": "Mood (1-5)"}


def astronaut_label(a):
    return a


@st.cache_resource
def get_conn():
    return connect(config.DB_URL)


def query(sql, params=None) -> pd.DataFrame:
    conn = get_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    except Exception:
        conn.rollback()
        raise


try:
    astronauts = query("SELECT DISTINCT astronaut_id FROM readings ORDER BY 1")["astronaut_id"].tolist()
except Exception as e:
    st.error("Cannot read from PostgreSQL. Start it with `docker compose up -d`, then run the consumer and producer.")
    st.code(str(e))
    st.stop()

if not astronauts:
    st.info("No readings yet. Run the consumer and the producer, then this page fills in live.")
    st.stop()

with st.sidebar:
    aid = st.selectbox("Astronaut", astronauts)
    live = st.toggle("Auto-refresh (3 s)", value=True)
    metric = st.selectbox("Chart metric", list(METRICS), format_func=METRICS.get)


@st.fragment(run_every=3 if live else None)
def board():
    df = query("SELECT * FROM readings WHERE astronaut_id=%s ORDER BY ts", (aid,))
    alerts = query("SELECT ts, indicator, value, level FROM alerts WHERE astronaut_id=%s ORDER BY ts DESC LIMIT 50", (aid,))
    total = query("SELECT COUNT(*) AS n, COALESCE(SUM((overall_level=2)::int),0) AS red FROM readings")
    latest = df.iloc[-1]
    lvl = int(latest["overall_level"])

    flagged_now = [a for a in alerts.itertuples() if a.ts == latest["ts"]]
    ui.banner(lvl, f"Current status: {LEVEL_NAMES[lvl]}",
              ", ".join(f"{a.indicator} ({LEVEL_NAMES[int(a.level)]})" for a in flagged_now) or "All indicators in the normal range.")
    st.caption(f"{astronaut_label(aid)} · mission day {int(latest['mission_day'])}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Readings (all crew)", int(total["n"][0]))
    c2.metric("Mission day", int(latest["mission_day"]))
    c3.metric("Alert-level readings (all crew)", int(total["red"][0]))

    st.subheader("Latest reading")
    cols = st.columns(4)
    for i, (col, key) in enumerate(FIELD_MAP.items()):
        l = lv(key, latest[col])
        cols[i % 4].markdown(
            f'<div class="vs-tile vs-l{l}"><div class="nm">{FIELDS[key]["label"]}</div>'
            f'<div class="val">{latest[col]:g}<small>{FIELDS[key]["unit"]}</small></div>{ui.badge(l)}</div>',
            unsafe_allow_html=True)

    preds = df["prediction"].apply(lambda p: p if isinstance(p, dict) else {})
    df["anomaly"] = preds.apply(lambda p: bool(p.get("anomaly_detected")))
    last = preds.iloc[-1]
    st.subheader("ML anomaly detection")
    if last.get("model_status") == "scored":
        m1, m2, m3 = st.columns(3)
        m1.metric("Anomaly detected", "Yes" if last["anomaly_detected"] else "No")
        m2.metric("Anomaly score", f"{last['anomaly_score']:.3f}")
        m3.metric("Review priority", str(last.get("review_priority", "-")).replace("_", " "))
        for r in last.get("risk_reasons") or []:
            st.caption(f"• {r}")
    else:
        st.info("Not enough history yet: the model needs 3 earlier readings per astronaut.")
    st.caption("Statistical anomaly detection on synthetic data. Not a medical diagnosis.")

    st.subheader("Trend")
    fig = px.line(df, x="ts", y=metric, markers=True, labels={"ts": "Time", metric: METRICS[metric]},
                  color_discrete_sequence=["#4fb8e0"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=10),
                      font_color="#8a9bb5", xaxis=dict(gridcolor="#1e2d45"), yaxis=dict(gridcolor="#1e2d45"))
    flagged = df[df["anomaly"]]
    if not flagged.empty:
        fig.add_scatter(x=flagged["ts"], y=flagged[metric], mode="markers", name="ML anomaly",
                        marker=dict(color="#e5534b", size=13, symbol="x"))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent alerts")
    if alerts.empty:
        st.success("No alerts for this astronaut.")
    else:
        alerts["level"] = alerts["level"].map(LEVEL_NAMES)
        st.dataframe(alerts, use_container_width=True, hide_index=True)


board()
