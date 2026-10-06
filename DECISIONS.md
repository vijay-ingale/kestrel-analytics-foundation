# Kestrel Analytics Foundation

**Decision summary:** Build a traceable metric layer first, with a usable explorer on top. Publish defined numbers and their coverage, not certainty the sources cannot support.

## What Is Delivered

Four feeds (POS, telemetry, WMS and ERP CDC) plus references become validated tables, tested models and a Streamlit explorer. The **14-entry KPI catalogue** records definitions, grain, exclusions, owners and limitations; **12 parameterized queries** cover sales, reconciliation, operations, history and quality. Two unsupported metrics are documented. The UI exposes SQL, filters, CSV export and sales source-row tracing.

**Stack:** Python for batch-bounded validation, PostgreSQL for established SQL/deployment patterns, dbt for tested transformations. More setup and loading cost than DuckDB; a familiar operational path. [README](README.md) provides the cold start.

## Key Judgments

| Source issue | Decision and consequence |
|---|---|
| Schema drift and quality | Versioned column mappings, typed validation, row quarantine and file/partition audits. Preserve provenance; collapse exact duplicates; exclude conflicting keys. Never zero-fill missing measurements or guess unknown units. |
| Sales units and channel | Revenue uses source quantity x source price. Eaches require known UOM/conversion: only **49.63%** of lines qualify. Use captured POS channel; retain historical master classification separately. |
| Temperature and time | Fahrenheit to Celsius; missing units inferred only from verified vendor conventions. Generator-supported timestamp convention/firmware correction. Excursions are reading-level, not trip-level. |
| Finance disagreement | Show duplicate/date effects and an unexplained residual: published totals are independently generated. Assume week labels are inclusive end dates; flag partial weeks. Do not force a match. |
| CDC and orders | Outlet history uses source time, sequence ties and deletion intervals. Later deletion sequences override reused order timestamps. Remove the generator-supported 8.5% partner uplift for comparison, not invoice reconciliation. |
| Warehouse cycle | Report a same-day STAGE-to-DISPATCH proxy with coverage. Only **31 groups (0.0021%)** qualify; this is not representative warehouse performance. |

## Deliberately Not Built

No carrier/trip joins or actual delivery SLA without identifiers/completion evidence. Approved templates expose SQL before read-only execution; unrestricted LLM SQL is deferred. Anomalies use an advisory 28-day three-sigma rule, not automatic exclusions. No forecasting, ML, statistical imputation or unstructured extraction: supplied feeds are Parquet. Authentication and scheduling remain future work.

## Next Two Weeks

**Week 1:** Agree historical UOM, trip/delivery identifiers, dock semantics and invoice reconciliation with owners; extend approved mappings and calibrate anomaly thresholds. **Week 2:** Add incremental loading, partitioned facts, monitoring, scheduling, authentication and a separately permissioned query service.

## Evidence and Production Boundary

**Scale 1:** 10,269,543 readable rows; **28m 42s**, **11.75 GiB**. All **21 models**, the invariant test, **12 queries** and **18 automated tests** passed. One corrupt file remains visible. [Verification details](docs/VERIFICATION.md).

Disk and full-rebuild duration limit growth first: **118 GiB at 10x**, **1.15 TiB at 100x**, excluding WAL/temporary space. These are untested projections; failure volume depends on disk and refresh window. Incremental processing, retention and workload separation precede a distributed engine.
