# Measured Verification

Measured on 6 October 2026 using the supplied generator, seed 20260811, scale 1, default 500,000-row slices. Python 3.12 ran in Docker Desktop on Windows, with PostgreSQL 16.10 and source files mounted from the host. Results describe this run, not a production benchmark.

| Check | Result |
|---|---|
| Supplied records, including unreadable file | 10,270,488 |
| Accepted source records | 10,269,543 |
| Corrupt files | 1; 945 expected telemetry records unavailable |
| End-to-end pipeline time | 1,722.07 seconds; 28 minutes 42 seconds |
| dbt transformation and invariant time | 167.41 seconds |
| PostgreSQL database size after build | 12,617,912,803 bytes; 11.75 GiB, excluding WAL and temporary spill |
| Full-scale build | 21 models and the invariant test passed |
| Automated tests | 18 passed; integration builds twice and UI interactions covered |
| Supported KPI query checks | All 12 executed successfully |
| Readable catalogue | Matches canonical JSON definitions |
| UI health | HTTP 200 at `/_stcore/health` |

Reproduce the evidence after building: `python -m pipeline.verify`. With Docker, use `docker compose run --rm pipeline python -m pipeline.verify`. The printed report contains row counts, coverage, source defects, and per-query execution checks. UI screenshot verification was unavailable in the session; Streamlit AppTest verified the functional views and interactions instead.

## Sales and Unit Coverage

4,084,000 landed POS rows become 4,000,000 distinct sales lines: 84,000 exact duplicates removed. All accepted distinct lines support revenue. Recorded gross sales are INR 5,508,198,259.46; net sales are INR 5,342,925,916.54. These describe the supplied POS coverage, not total company revenue.

Only 1,985,099 lines support confirmed eaches, **49.63%** of distinct sales lines. 1,998,980 lack source UOM, principally the pre-upgrade schema; 15,921 lack a required case conversion. Those lines remain available for other eligible measures. No historical UOM was guessed from prices or current product attributes.

## Temperature Normalization

3,713,926 readable telemetry rows become 3,598,770 distinct readings after removing 115,156 duplicates. 3,577,294 have usable temperatures; 21,476 have missing measurements.

On this same distinct valid-reading population, a naive `temp_value > 8` test flags 1,369,598 readings, **38.29%**. The Celsius-normalized rule flags 257,204, **7.19%**. Vendor conventions resolve 287,301 missing-unit readings; 328,061 readings receive the known firmware clock correction. These are reading-level results. No trip-level or carrier-level rate is claimed.

## Missing Data and CDC

- `reefer_telemetry/dt=2025-07-14/part-00000.parquet` is unreadable. The partition stays marked incomplete even though its other files are usable.
- `GW-017` has no observed readings on 11 and 12 February 2026 while those partitions otherwise reconcile. These are candidate gateway outages, not proof of an expected sampling frequency.
- 1,637 manifest-covered partitions reconcile; one has an unreadable file. The 1,634 ERP partitions have no supplied manifest and are labeled `NO_MANIFEST`.
- 2,880 current orders are tombstoned despite stale deletion timestamps. Source deletion sequences and the exception flag remain inspectable.
- No conflicting business-key payloads were found in the generated full dataset. The defect fixture proves conflicts are detected and excluded when present.

## Warehouse and Finance Limits

Of 1,495,173 observed order/warehouse/day groups, only **31** have eligible STAGE-to-DISPATCH boundaries: **0.0021%** coverage. 1,495,127 lack a boundary and 15 have reversed timestamps. This synthetic feed cannot support a representative warehouse performance claim. The query exposes the qualified proxy, sample counts, and coverage; the UI warns on very low coverage.

Finance reconciliation balances duplicate, conflicting-key, and date effects plus an unexplained residual for each published week/channel. The supplied generator creates Finance totals independently of POS, so an exact match would be fabricated. Partial weeks and unpublished source buckets remain distinct. Actual delivery SLA and chilled-trip rates by carrier remain unavailable without additional source evidence.

## Capacity Interpretation

Input batches are bounded, but full normalization and analytical rebuilds are expensive. A simple row-proportional storage projection is about 118 GiB at 10x and 1.15 TiB at 100x, before WAL, temporary sorts, and retained runs. These are projections, not tested capacities. Disk and rebuild duration are the first limits; incremental loading and partitioned facts should precede larger deployment.
