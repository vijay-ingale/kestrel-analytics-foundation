import argparse
import os
from pathlib import Path
import time
from urllib.parse import unquote, urlparse

import psycopg
from psycopg.types.json import Jsonb

from pipeline.ingest import bootstrap, ingest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "postgresql://kestrel:kestrel_local@localhost:15432/kestrel"


def dbt_build(url):
    from dbt.cli.main import dbtRunner
    parsed = urlparse(url)
    for key, value in {"PGHOST":parsed.hostname, "PGPORT":str(parsed.port or 5432), "PGUSER":unquote(parsed.username or ""), "PGPASSWORD":unquote(parsed.password or ""), "PGDATABASE":parsed.path.lstrip("/")}.items():
        os.environ[key] = value
    result = dbtRunner().invoke(["build", "--project-dir", str(ROOT / "dbt"), "--profiles-dir", str(ROOT / "dbt"), "--fail-fast"])
    if not result.success:
        raise RuntimeError(f"dbt build failed: {result.exception or 'see dbt logs'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT.parent / "data")
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--ingest-only", action="store_true")
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("batch-size must be positive")
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    started = time.monotonic()
    with psycopg.connect(url, autocommit=True) as conn:
        if not conn.execute("SELECT pg_try_advisory_lock(710482)").fetchone()[0]:
            raise RuntimeError("Another build is running")
        bootstrap(conn)
        run_id = conn.execute("INSERT INTO audit.runs (status,data_path) VALUES ('RUNNING',%s) RETURNING run_id", (str(args.data.resolve()),)).fetchone()[0]
        try:
            with conn.transaction():
                ingest(conn, args.data, run_id, args.batch_size)
            if not args.ingest_only:
                dbt_build(url)
            details = {"elapsed_seconds":round(time.monotonic() - started, 2)}
            status = "INGESTED" if args.ingest_only else "SUCCESS"
            conn.execute("UPDATE audit.runs SET status=%s,finished_at=now(),details=%s WHERE run_id=%s", (status,Jsonb(details),run_id))
            print(f"Run {run_id}: {status} in {details['elapsed_seconds']} seconds", flush=True)
        except Exception as error:
            conn.execute("UPDATE audit.runs SET status='FAILED',finished_at=now(),details=%s WHERE run_id=%s", (Jsonb({"error":str(error)}),run_id))
            raise


if __name__ == "__main__":
    main()
