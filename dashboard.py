"""Small Streamlit dashboard from demo jsonl or Kafka output saved to the same format."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Astronaut AI — ML Monitoring (Demo)', layout='wide')
st.title('Astronaut AI | Statistical Anomaly Monitoring')
st.warning('Research prototype only. Not medical decision support or spacecraft safety alerting. Historic CSV replay is not live sensor data.')
path = Path(__file__).resolve().parent / 'sample_dashboard_events.jsonl'
if not path.exists():
    st.info('Run python offline_demo.py first to generate sample events.')
    st.stop()
items = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]
df = pd.DataFrame([{k: v for k, v in x.items() if k != 'features'} for x in items])
source = st.selectbox('Dataset', df.source.unique())
selected = df.loc[df.source.eq(source)].copy()
a, b, c = st.columns(3)
a.metric('Messages', len(selected))
b.metric('Statistical anomalies', int(selected.is_anomaly.sum()))
c.metric('Typical measurements', int((~selected.is_anomaly).sum()))
st.line_chart(selected.reset_index(drop=True)['anomaly_score'])
st.dataframe(selected[['timestamp', 'entity_id', 'anomaly_score', 'is_anomaly', 'status', 'interpretation']], use_container_width=True)
