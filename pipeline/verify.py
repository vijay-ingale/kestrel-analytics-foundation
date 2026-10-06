"""Check every catalogue query and print measured data-quality evidence."""
import json
import os
import psycopg
from psycopg.rows import dict_row
from pipeline.build import DEFAULT_URL
from pipeline.query import CATALOGUE, execute, parameters


def main():
    url = os.environ.get("DATABASE_URL",DEFAULT_URL)
    with psycopg.connect(url,row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '60s'")
        bounds = conn.execute("SELECT min(calendar_date) AS first_day,max(calendar_date) AS last_day FROM reference.fiscal_calendar").fetchone()
        evidence = {
            "run":conn.execute("SELECT run_id,status,details FROM audit.runs ORDER BY run_id DESC LIMIT 1").fetchone(),
            "database_bytes":conn.execute("SELECT pg_database_size(current_database()) AS bytes").fetchone()["bytes"],
            "files":conn.execute("SELECT feed,status,count(*) AS files,sum(accepted_rows) AS accepted_rows,sum(rejected_rows) AS rejected_rows FROM audit.files WHERE run_id=(SELECT max(run_id) FROM audit.files) GROUP BY 1,2 ORDER BY 1,2").fetchall(),
            "coverage":conn.execute("SELECT sum(sales_lines) AS sales_lines,sum(revenue_eligible_lines) AS revenue_eligible_lines,sum(units_eligible_lines) AS units_eligible_lines,sum(missing_uom_lines) AS missing_uom_lines,sum(missing_conversion_lines) AS missing_conversion_lines FROM analytics.mart_sales_daily").fetchone(),
            "gateway_gaps":conn.execute("SELECT * FROM analytics.mart_gateway_gaps ORDER BY missing_date,gateway_id LIMIT 20").fetchall(),
            "completeness":conn.execute("SELECT completeness_status,count(*) AS partitions FROM analytics.mart_feed_completeness GROUP BY 1 ORDER BY 1").fetchall(),
            "deleted_orders":conn.execute("SELECT count(*) FILTER (WHERE is_deleted) AS deleted_orders,count(*) FILTER (WHERE deletion_timestamp_exception) AS stale_delete_timestamps FROM analytics.fct_orders").fetchone(),
            "cycles":conn.execute("SELECT cycle_status,count(*) AS order_warehouse_days FROM analytics.mart_warehouse_cycles GROUP BY 1 ORDER BY 1").fetchall(),
        }
        txn = conn.execute("SELECT txn_id FROM analytics.fct_sales ORDER BY txn_id LIMIT 1").fetchone()["txn_id"]
    params = parameters(bounds["first_day"],bounds["last_day"],lookup_key=txn)
    query_checks = []
    for metric in CATALOGUE:
        if metric["supported"]:
            rows,truncated = execute(metric["id"],params)
            query_checks.append({"metric":metric["id"],"returned_rows":len(rows),"truncated":truncated})
    print(json.dumps({"evidence":evidence,"query_checks":query_checks},default=str,indent=2))


if __name__ == "__main__":
    main()
