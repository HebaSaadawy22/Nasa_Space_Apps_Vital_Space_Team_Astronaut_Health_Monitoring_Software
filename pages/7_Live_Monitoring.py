"""Live monitoring page: reads the readings and alerts that the Kafka consumer saved to PostgreSQL."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.health_engine import level as lv
from src.utils.constants import LEVEL_COLORS, LEVEL_NAMES
from streaming import config
from streaming.db import connect
from streaming.risk import FIELD_MAP, assess
from src.utils.constants import FIELDS

st.set_page_config(page_title="Live Monitoring · Vital Space", page_icon="📡", layout="wide")
st.title("📡 Live Monitoring")
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readings (all crew)", int(total["n"][0]))
    c2.metric("Mission day", int(latest["mission_day"]))
    c3.metric("Alert-level readings (all crew)", int(total["red"][0]))
    c4.markdown(f"**Current status**<br><span style='color:{LEVEL_COLORS[lvl]};font-size:1.6rem'>● {LEVEL_NAMES[lvl]}</span>",
                unsafe_allow_html=True)

    st.subheader(f"Latest reading · {astronaut_label(aid)} · day {int(latest['mission_day'])}")
    cols = st.columns(4)
    for i, (col, key) in enumerate(FIELD_MAP.items()):
        l = lv(key, latest[col])
        cols[i % 4].markdown(
            f"**{FIELDS[key]['label']}**<br><span style='font-size:1.4rem'>{latest[col]:g} "
            f"<small>{FIELDS[key]['unit']}</small></span><br><span style='color:{LEVEL_COLORS[l]}'>● {LEVEL_NAMES[l]}</span>",
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
    fig = px.line(df, x="ts", y=metric, markers=True, labels={"ts": "Time", metric: METRICS[metric]})
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
