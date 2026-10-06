from datetime import timedelta
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import altair as alt
import pandas as pd
import psycopg
from psycopg.rows import dict_row
import streamlit as st

from pipeline.build import DEFAULT_URL
from pipeline.query import CATALOGUE, METRICS, execute, parameters, query_sql

st.set_page_config(page_title="Kestrel | Analytics",page_icon=":material/query_stats:",layout="wide")
st.title("Kestrel Analytics")


def read(query):
    with psycopg.connect(os.environ.get("DATABASE_URL",DEFAULT_URL),row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '15s'")
        return conn.execute(query).fetchall()


try:
    run = read("SELECT run_id,started_at,finished_at,status,details FROM audit.runs ORDER BY run_id DESC LIMIT 1")
    if not run or run[0]["status"] != "SUCCESS":
        st.warning("Metrics unavailable: the latest pipeline run has not succeeded.")
        if run:
            st.json(run[0],expanded=False)
        st.stop()
    bounds = read("SELECT min(calendar_date) AS first_day,max(calendar_date) AS last_day FROM reference.fiscal_calendar")[0]
    warehouses = read("SELECT warehouse_code,warehouse_name FROM reference.warehouse_master ORDER BY warehouse_code")
except psycopg.Error:
    st.error("Database unavailable. Start PostgreSQL and run the pipeline using the README commands.")
    st.stop()

with st.sidebar:
    st.subheader("Reporting Period")
    start = st.date_input("From",bounds["first_day"],min_value=bounds["first_day"],max_value=bounds["last_day"])
    end = st.date_input("Through",bounds["last_day"],min_value=bounds["first_day"],max_value=bounds["last_day"])
    channel = st.selectbox("POS channel",["","GT","MT","HORECA","ECOM"],format_func=lambda value:value or "All channels")
    warehouse = st.selectbox("Warehouse",[""]+[row["warehouse_code"] for row in warehouses],format_func=lambda value:value or "All warehouses")
    st.divider()
    st.caption(f"Run {run[0]['run_id']} | {run[0]['status']}")
    st.caption(f"Completed {run[0]['finished_at']:%Y-%m-%d %H:%M UTC}")
    if st.button("Refresh",icon=":material/refresh:",use_container_width=True):
        st.rerun()

if start > end:
    st.error("From date must precede Through date.")
    st.stop()
params = parameters(start,end,channel,warehouse)


def results(metric_id, custom=None, chart=False):
    metric = METRICS[metric_id]
    st.subheader(metric["name"])
    st.caption(metric["definition"])
    if not metric["supported"]:
        st.warning(metric["limitations"])
        return
    try:
        rows,truncated = execute(metric_id,custom or params)
    except (psycopg.Error,RuntimeError,ValueError) as error:
        st.error(str(error))
        return
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("No eligible records for this selection.")
    else:
        for column in frame.columns:
            if column.endswith(("_inr","_pct","_minutes")) or column in ("units_eaches","confirmed_units_eaches","z_score"):
                frame[column] = pd.to_numeric(frame[column],errors="coerce")
        if chart and metric_id == "sales":
            st.altair_chart(alt.Chart(frame).mark_bar(color="#087f5b").encode(x=alt.X("channel:N",title="Channel"),y=alt.Y("gross_sales_inr:Q",title="Gross sales (INR)"),tooltip=["channel","gross_sales_inr"]),use_container_width=True)
        elif chart and metric_id == "cold":
            st.altair_chart(alt.Chart(frame).mark_line(point=True).encode(x="month:T",y=alt.Y("excursion_rate_pct:Q",title="Reading excursion rate (%)"),color="telemetry_vendor:N",tooltip=["month:T","telemetry_vendor","excursion_rate_pct"]),use_container_width=True)
        st.dataframe(frame,hide_index=True,use_container_width=True)
        st.download_button("Download results",frame.to_csv(index=False),f"kestrel_{metric_id}.csv","text/csv",icon=":material/download:",key=f"download_{metric_id}_{st.session_state.get('view','')}")
        if truncated:
            st.warning("Showing the first 5,000 rows; narrow the selection for a complete export.")
    with st.expander("Definition, Coverage, and SQL"):
        st.write(f"**Grain:** {metric['grain']}")
        st.write(f"**Exclusions:** {metric['exclusions']}")
        st.write(f"**Limitations:** {metric['limitations']}")
        st.write(f"**Owner:** {metric['owner']}")
        st.code(query_sql(metric_id),language="sql")


view = st.segmented_control("Workspace",["Business","Operations","Reconciliation","Data Quality","Questions & Trace","Catalogue"],default="Business",key="view")
if view == "Business":
    metric = st.selectbox("Metric",["sales","units","fiscal_sales","outlets","orders"],format_func=lambda value:METRICS[value]["name"])
    if metric == "fiscal_sales":
        as_of = st.date_input("As of",bounds["last_day"] + timedelta(days=1))
        results(metric,dict(params,as_of=as_of))
    else:
        results(metric,chart=True)
elif view == "Operations":
    metric = st.selectbox("Metric",["cold","cycles","trips","service"],format_func=lambda value:METRICS[value]["name"])
    results(metric,chart=True)
elif view == "Reconciliation":
    if warehouse:
        st.caption("Finance reconciliation covers all warehouses; POS channel and week-ending filters apply.")
    results("finance")
elif view == "Data Quality":
    metric = st.selectbox("Quality Check",["completeness","gateway","anomalies"],format_func=lambda value:METRICS[value]["name"])
    results(metric)
    with st.expander("Ingestion Rejections and Key Conflicts"):
        st.dataframe(pd.DataFrame(read("SELECT feed,source_file,source_row,reasons FROM audit.quarantine WHERE run_id = (SELECT max(run_id) FROM audit.files) LIMIT 200")),hide_index=True)
        st.dataframe(pd.DataFrame(read("SELECT * FROM analytics.mart_key_conflicts LIMIT 200")),hide_index=True)
        st.dataframe(pd.DataFrame(read("SELECT feed,source_file,status,details FROM audit.files WHERE run_id = (SELECT max(run_id) FROM audit.files) AND (status <> 'OK' OR details->'extra_columns' <> '[]'::jsonb) LIMIT 200")),hide_index=True)
elif view == "Questions & Trace":
    metric = st.selectbox("Question",[item["id"] for item in CATALOGUE],format_func=lambda value:METRICS[value]["question"])
    if not METRICS[metric]["supported"]:
        st.warning(METRICS[metric]["limitations"])
    else:
        local = dict(params)
        if metric == "trace":
            local["lookup_key"] = st.text_input("Transaction ID")
        if metric == "fiscal_sales":
            local["as_of"] = st.date_input("As of",bounds["last_day"] + timedelta(days=1))
        st.code(query_sql(metric),language="sql")
        st.json({key:str(value) for key,value in local.items()},expanded=False)
        if st.button("Run query",icon=":material/play_arrow:",type="primary"):
            results(metric,local)
elif view == "Catalogue":
    for metric in CATALOGUE:
        with st.expander(metric["name"] + (" | unavailable" if not metric["supported"] else "")):
            st.write(metric["definition"])
            st.write(f"**Grain:** {metric['grain']}")
            st.write(f"**Exclusions:** {metric['exclusions']}")
            st.write(f"**Sources:** {', '.join(metric['sources'])}")
            st.write(f"**Owner:** {metric['owner']}")
            st.write(f"**Limitations:** {metric['limitations']}")
