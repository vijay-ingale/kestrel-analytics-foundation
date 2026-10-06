"""Read-only execution of catalogue SQL with bound parameters and resource limits."""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
import sqlparse

from pipeline.build import DEFAULT_URL

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = json.loads((ROOT / "docs/kpi_catalogue.json").read_text())
METRICS = {metric["id"]: metric for metric in CATALOGUE}


def query_sql(metric_id):
    if metric_id not in METRICS:
        raise ValueError("Unknown catalogue metric")
    metric = METRICS[metric_id]
    if not metric["supported"]:
        raise ValueError(metric["limitations"])
    query = (ROOT / "sql/kpis" / metric["sql"]).read_text().strip().rstrip(";")
    statements = sqlparse.parse(query)
    if len(statements) != 1 or statements[0].get_type() != "SELECT":
        raise ValueError("Catalogue query must contain one SELECT statement")
    return query


def parameters(start, end, channel="", warehouse="", lookup_key="", as_of=None):
    start = date.fromisoformat(str(start))
    end = date.fromisoformat(str(end))
    if start > end:
        raise ValueError("Start date must not follow end date")
    if channel not in ("", "GT", "MT", "HORECA", "ECOM"):
        raise ValueError("Unsupported channel")
    return dict(start=start,end=end,channel=channel,warehouse=warehouse,lookup_key=lookup_key,as_of=as_of or end + timedelta(days=1))


def execute(metric_id, params, limit=5000):
    query = query_sql(metric_id)
    if not 1 <= limit <= 5000:
        raise ValueError("Result limit must be between 1 and 5000")
    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_URL), row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '3s'")
        latest = conn.execute("SELECT status FROM audit.runs ORDER BY run_id DESC LIMIT 1").fetchone()
        if not latest or latest["status"] != "SUCCESS":
            raise RuntimeError("Metrics unavailable until the latest pipeline run succeeds")
        rows = conn.execute(f"SELECT * FROM ({query}) catalogue_result LIMIT {limit + 1}", params).fetchall()
    return rows[:limit], len(rows) > limit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("metric", choices=list(METRICS))
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2026-06-30")
    parser.add_argument("--channel", default="")
    parser.add_argument("--warehouse", default="")
    parser.add_argument("--lookup-key", default="")
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    params = parameters(args.start,args.end,args.channel,args.warehouse,args.lookup_key,args.as_of)
    print(query_sql(args.metric))
    rows, truncated = execute(args.metric,params)
    print(json.dumps({"parameters":params,"rows":rows,"truncated":truncated}, default=str,indent=2))


if __name__ == "__main__":
    main()
