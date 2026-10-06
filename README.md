# Kestrel Analytics Foundation

Validated ingestion, documented metrics, Finance reconciliation, and an inspectable query explorer for the Kestrel assessment. Read [DECISIONS.md](DECISIONS.md) first. Metric definitions live in the single [KPI catalogue](docs/kpi_catalogue.json), also rendered in the UI.

## Cold Start With Docker

Requires Docker Desktop with Linux containers, Docker Compose, and the supplied assessment dataset. No cloud account or API key is required. Run these commands from this repository:

```sh
docker compose build
docker compose up -d db
docker compose run --rm pipeline
docker compose up -d ui
```

Open **http://localhost:8501**. The default data path is `../data`, mounted read-only at `/data`. It must contain `raw/`, `reference/`, and `_manifest/expected_partitions.csv`. To use another path, set `KESTREL_DATA_DIR` before running Compose:

```powershell
$env:KESTREL_DATA_DIR='C:/Users/vijay/assessment/dataset_scale1'
```

```sh
export KESTREL_DATA_DIR=/absolute/path/to/data
```

PostgreSQL is bound to localhost port **15432**, UI to **8501**. Local defaults are `kestrel` / `kestrel_local`, database `kestrel`; `.env.example` lists overrides. These defaults are for this local assessment, not production credentials. If the database port is occupied or reserved, set `KESTREL_DB_PORT` in `.env`. Containers connect internally on 5432.

## Data Generation

The assignment generator and dataset are deliberately outside this submission. With the supplied `generate_dataset.py` available in the parent directory:

```sh
python -m pip install numpy==2.3.3 pandas==2.3.3 pyarrow==21.0.0
python ../generate_dataset.py --scale 1 --out ../dataset_scale1
```

**Use a new output directory:** the supplied generator deletes an existing output directory. Set `KESTREL_DATA_DIR` to the generated path. Scale 10 uses the same command with `--scale 10` and a separate output path; no scale-10 performance claim is made.

## Local Python Alternative

Python 3.12 or 3.13 and the same PostgreSQL service are required:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
docker compose up -d db
.venv/Scripts/python.exe -m pipeline.build --data ../dataset_scale1
.venv/Scripts/python.exe -m streamlit run app/main.py
```

On Linux/macOS, use `.venv/bin/python`. `DATABASE_URL` overrides the local database connection; changing `.env` affects Compose, while local Python requires an exported environment variable. `--batch-size 10000` bounds input batches. `--ingest-only` loads and audits sources without publishing a successful analytical build.

## Query the Metrics

```sh
python -m pipeline.query sales --start 2026-04-01 --end 2026-06-30
python -m pipeline.query fiscal_sales --as-of 2026-07-01
python -m pipeline.query units --start 2026-06-01 --end 2026-06-30
python -m pipeline.query finance --channel MT
python -m pipeline.query trace --lookup-key T0-000000001
```

Use the virtual-environment Python when running locally. Queries print their SQL, parameters, and JSON results. [sql/kpis](sql/kpis) contains the runnable, parameterized PostgreSQL SQL behind the catalogue. The UI's Questions & Trace view uses those same queries. Supported questions are approved templates, not unrestricted natural-language SQL generation. Transactions are read-only, timeout-limited, and capped at 5,000 returned rows; aggregation happens before that cap. Unsupported trip/carrier and delivery-SLA questions explain the missing evidence.

## Model and Quality Policies

```mermaid
flowchart LR
    A[External Parquet and CSV] --> B[Versioned contracts and validation]
    B --> C[PostgreSQL raw and reference]
    B --> D[Audit and quarantine]
    C --> E[dbt staging and historical dimensions]
    E --> F[Facts and KPI marts]
    F --> G[SQL library and Streamlit]
    D --> G
```

- Columns, units, types, timestamps, and aliases are explicitly mapped in [contracts/feeds.json](contracts/feeds.json). Unknown columns are reported and remain in the original file; unsupported required schema changes reject that file. Optional column absence differs from a required-column failure. Conflicting aliases and unit metadata are quarantined.
- Accepted rows retain relative source path, one-based file row number, complete-source-payload SHA-256, schema version, and validation issues. Original files remain the provenance source. Quarantined rows retain their payload and reason codes. Exact duplicates retain one representative; conflicting business keys are excluded and listed separately.
- Missing optional values remain null. Missing price/quantity only excludes the affected measures. Missing UOM or conversion factors never become guessed eaches. Pre-upgrade quantities therefore have no confirmed eaches total. Negative quantities remain visible with review flags; returns are not silently discarded.
- UTC POS timestamps become Asia/Kolkata business dates. WMS timestamps are local to the warehouse. Telemetry follows the generator's UTC-labeled convention and corrects firmware 2.1.4 by seven hours. Fahrenheit conversion and vendor-based missing-unit inference retain source values and resolution evidence.
- Outlet history applies source-time ordering, sequence tie-breaking, and deletion intervals. Orders expose the generator's stale deletion timestamp exception and honor later deletion sequences. PARTNER_API raw and adjusted values are both retained; the 1.085 correction is synthetic-generator evidence, not an invoice reconciliation.
- STAGE-to-DISPATCH durations are same-day proxies with exactly one scan at each boundary. Missing, reversed, ambiguous, and cross-day pairs are not eligible. Coverage is reported. Trip-level cold-chain and actual on-time delivery cannot be calculated defensibly from these sources.
- Manifest checks include expected files, readable rows, bytes, and missing days. ERP has no supplied manifest and is marked accordingly. Gateway zero-activity days are candidate outages; no sampling-frequency assumption is invented. Sales three-sigma flags use prior history only and are advisory, not automatic exclusions.
- Finance weeks are interpreted as inclusive seven-day periods ending on each label. Boundary weeks are flagged. Reconciliation displays duplicate, conflicting-key, and date effects plus a residual: the generator creates published totals independently. Zeroes in this bridge indicate no observed sales contribution, not certified zero business activity; consult completeness.

## Tests and Failure Behavior

```sh
python -m pytest -q
docker compose exec -T db createdb -U kestrel kestrel_test
```

To include integration checks, set `KESTREL_TEST_DATABASE_URL=postgresql://kestrel:kestrel_local@localhost:15432/kestrel_test` and rerun pytest. The test refuses another database name and rebuilds only its test schema. It exercises duplicates, conflicting keys, nulls, corrupt files, conversion gaps, timezone boundaries, historical channel ties, deletion timestamp exceptions, reconciliation balance, and two identical pipeline runs. dbt's invariant test runs automatically during every pipeline build.

Each build takes an advisory lock. Source replacement is transactional; a fatal ingestion error rolls it back. Unreadable individual files are recorded and do not masquerade as complete input. Analytical models rebuild afterward; publication is **not an atomic model swap**. The UI and query runner block metrics unless the latest run is successful, including after a partial dbt failure. Fix the cause and rerun the documented pipeline command. Hard process termination can leave RUNNING status; inspect the audit and rerun after confirming no build is active.

Audit runs and rejection evidence are retained; input is replaced rather than appended, so rerunning does not double counts. Audit retention and incremental processing are deferred. All supplied raw feeds must contain at least one usable row. Invalid reference schemas, duplicate reference keys, and invalid case factors fail the build.

## Troubleshooting and Scale

`docker compose logs db` and `docker compose logs ui` show service errors. `dbt/logs/dbt.log` contains local transformation details; `audit.runs`, `audit.files`, and `audit.quarantine` contain pipeline evidence. A missing `raw/` means the dataset must be supplied or generated; widening globs will not repair corrupt files. Database startup can take several seconds; Compose waits for its health check.

The input iterator bounds batch memory, but PostgreSQL still needs disk for raw rows, analytical tables, and sort spill. Full rebuilds, payload hashing, and database sorts are the expected first limits at larger volume. This submission does not claim tested 10x/100x capacity. Use measured runtime and database size to plan incremental loading, partitioned facts, and workload separation. Do not commit datasets, database volumes, `.env`, or generated outputs.
