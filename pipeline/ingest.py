"""Bounded-memory COPY ingestion with file-level rollback and source provenance."""
import csv
import json
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb
import pyarrow.parquet as pq

from pipeline.contracts import CONTRACTS, inspect_schema, normalize, parse

REFERENCES = {
    "uom_conversion": {"sku_code":"text", "eaches_per_case":"numeric", "base_uom":"text", "case_uom":"text"},
    "warehouse_master": {"warehouse_code":"text", "warehouse_name":"text", "city":"text", "region_name":"text", "timezone":"text", "chilled_capacity_pallets":"bigint"},
    "carrier_master": {"carrier_id":"text", "carrier_name":"text", "mode":"text", "sla_hours":"numeric", "rate_per_km":"numeric"},
    "fiscal_calendar": {"calendar_date":"date", "fiscal_year":"text", "fiscal_quarter":"text", "fiscal_month_no":"bigint", "iso_week":"bigint", "day_of_week":"text", "is_weekend":"bigint"},
    "legacy_finance_weekly_report": {"week_ending":"date", "channel":"text", "gross_sales_inr":"numeric", "units_sold":"numeric", "basket_count":"bigint", "prepared_by":"text", "note":"text"},
}
META = {"_hash":"text", "_file":"text", "_row":"bigint", "_partition":"date", "_schema_version":"text", "_issues":"text[]"}


def bootstrap(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS audit")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit.runs (
        run_id bigserial PRIMARY KEY, started_at timestamptz NOT NULL DEFAULT now(),
        finished_at timestamptz, status text NOT NULL, data_path text NOT NULL, details jsonb)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit.files (
        run_id bigint, feed text, partition text, source_file text, status text,
        observed_rows bigint, accepted_rows bigint, rejected_rows bigint, bytes bigint,
        schema_version text, details jsonb)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit.quarantine (
        run_id bigint, feed text, source_file text, source_row bigint, reasons text[], payload jsonb)""")


def create_table(conn, schema, name, fields):
    definitions = sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(key), sql.SQL(kind)) for key, kind in fields.items())
    conn.execute(sql.SQL("CREATE TABLE {}.{} ({})").format(sql.Identifier(schema), sql.Identifier(name), definitions))


def copy_statement(schema, table, fields):
    return sql.SQL("COPY {}.{} ({}) FROM STDIN").format(sql.Identifier(schema), sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, fields)))


def ingest(conn, data, run_id, batch_size=10000):
    data = Path(data).resolve()
    if not (data / "raw").is_dir():
        raise FileNotFoundError(f"No raw feeds at {data / 'raw'}. Supply or regenerate the assignment dataset.")
    conn.execute("DROP SCHEMA IF EXISTS raw CASCADE")
    conn.execute("CREATE SCHEMA raw")
    conn.execute("DROP SCHEMA IF EXISTS reference CASCADE")
    conn.execute("CREATE SCHEMA reference")
    for table, fields in REFERENCES.items():
        create_table(conn, "reference", table, fields)
        with (data / "reference" / f"{table}.csv").open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if set(fields) - set(reader.fieldnames or []):
                raise ValueError(f"Reference schema mismatch: {table}")
            with conn.cursor().copy(copy_statement("reference", table, fields)) as copy:
                for row in reader:
                    copy.write_row(tuple(parse(row[key], kind) for key, kind in fields.items()))
    for table, key in (("uom_conversion","sku_code"), ("warehouse_master","warehouse_code"), ("carrier_master","carrier_id"), ("fiscal_calendar","calendar_date")):
        conn.execute(sql.SQL("ALTER TABLE reference.{} ADD PRIMARY KEY ({})").format(sql.Identifier(table), sql.Identifier(key)))
    if conn.execute("SELECT count(*) FROM reference.uom_conversion WHERE eaches_per_case IS NULL OR eaches_per_case <= 0").fetchone()[0]:
        raise ValueError("Reference conversion factors must be positive")
    for feed, contract in CONTRACTS.items():
        fields = dict(contract["fields"], **META)
        create_table(conn, "raw", contract["table"], fields)
        root = data / "raw" / feed
        files = sorted(root.glob(f"{contract['partition']}=*/*.parquet"))
        if not files:
            raise FileNotFoundError(f"Required feed has no Parquet files: {feed}")
        total = 0
        for index, path in enumerate(files):
            partition = path.parent.name
            partition_date = partition.split("=", 1)[1]
            source_file = path.relative_to(data).as_posix()
            observed = accepted = rejected = 0
            version, extras = "unknown", []
            status, detail = "OK", {}
            try:
                with conn.transaction():
                    parquet = pq.ParquetFile(path)
                    version, missing, extras = inspect_schema(feed, parquet.schema_arrow.names, partition_date)
                    if missing:
                        raise ValueError(f"Required schema columns missing: {missing}")
                    for batch in parquet.iter_batches(batch_size=batch_size):
                        accepted_batch, rejected_batch = [], []
                        for row in batch.to_pylist():
                            observed += 1
                            mapped, errors, warnings, fingerprint = normalize(feed, row)
                            if errors:
                                rejected += 1
                                rejected_batch.append((run_id, feed, source_file, observed, errors, Jsonb(row, dumps=lambda value: json.dumps(value, default=str))))
                            else:
                                accepted += 1
                                mapped.update(_hash=fingerprint, _file=source_file, _row=observed, _partition=parse(partition_date, "date"), _schema_version=version, _issues=warnings)
                                accepted_batch.append(tuple(mapped[key] for key in fields))
                        with conn.cursor().copy(copy_statement("raw", contract["table"], fields)) as copy:
                            for row in accepted_batch:
                                copy.write_row(row)
                        if rejected_batch:
                            with conn.cursor().copy("COPY audit.quarantine FROM STDIN") as copy:
                                for row in rejected_batch:
                                    copy.write_row(row)
                    detail = {"extra_columns":extras, "metadata_rows":parquet.metadata.num_rows}
                    if observed != parquet.metadata.num_rows:
                        raise ValueError("Read count does not match Parquet metadata")
            except (OSError, ValueError) as error:
                status = "REJECTED_FILE"
                detail = {"error":str(error), "extra_columns":extras}
                observed = accepted = rejected = 0
            conn.execute("INSERT INTO audit.files VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (run_id,feed,partition,source_file,status,observed,accepted,rejected,path.stat().st_size,version,Jsonb(detail)))
            total += accepted
            if (index + 1) % 500 == 0:
                print(f"{feed}: {index + 1}/{len(files)} files; {total:,} accepted", flush=True)
        if total == 0:
            raise ValueError(f"No usable records in required feed {feed}")
        print(f"{feed}: {total:,} accepted rows", flush=True)
    create_table(conn, "reference", "expected_partitions", {"feed":"text", "partition":"text", "file_count":"bigint", "row_count":"bigint", "bytes":"bigint"})
    with (data / "_manifest/expected_partitions.csv").open(newline="", encoding="utf-8-sig") as source:
        with conn.cursor().copy("COPY reference.expected_partitions FROM STDIN") as copy:
            for row in csv.DictReader(source):
                copy.write_row((row["feed"],row["partition"],int(row["file_count"]),int(row["row_count"]),int(row["bytes"])))
    conn.execute("ALTER TABLE reference.expected_partitions ADD PRIMARY KEY (feed, partition)")
    for contract in CONTRACTS.values():
        conn.execute(sql.SQL("ANALYZE raw.{}").format(sql.Identifier(contract["table"])))
