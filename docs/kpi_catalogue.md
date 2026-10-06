# KPI Catalogue

Generated from `docs/kpi_catalogue.json`; edit that source and run `python -m pipeline.catalogue`.

## Sales and Basket Count

Gross sales = source quantity times source unit price, before tax and discounts. Net sales subtract recorded line discounts. Basket count is distinct nonnull source basket IDs within the selected period and channel.

**Grain:** Captured POS channel across selected business dates

**Filters and Exclusions:** Invalid required fields and conflicting transaction keys. Null quantity/price excluded from revenue; null discounts excluded from net sales. Null basket IDs excluded from basket count.

**Proposed Owner:** Finance (proposed)

**Known Limitations:** POS partner coverage only; historical outlet channel is retained separately. Missing source UOM does not change source-price arithmetic. Negative amounts remain flagged for review. Basket IDs can span source channels; counts are not additive across channels or dates.

**Sources:** POS, ERP outlet CDC

**Query:** [sales.sql](../sql/kpis/sales.sql)

## Last Complete Fiscal Quarter Sales

Gross sales in the fiscal quarter immediately preceding the quarter containing as_of. Fiscal year begins in April.

**Grain:** Fiscal year, quarter, channel

**Filters and Exclusions:** Same exclusions as gross sales; require full calendar coverage of the quarter.

**Proposed Owner:** Finance (proposed)

**Known Limitations:** Calendar completeness does not guarantee feed completeness; consult partition checks. as_of is explicit, defaulting to the day after dataset end.

**Sources:** POS, fiscal calendar

**Query:** [fiscal_sales.sql](../sql/kpis/fiscal_sales.sql)

## Confirmed Units in Eaches

EA quantities plus CS quantities multiplied by the SKU eaches-per-case reference factor.

**Grain:** Captured POS channel within selected business dates

**Filters and Exclusions:** Rows with missing UOM, quantity, or required conversion factor.

**Proposed Owner:** Commercial Operations (proposed)

**Known Limitations:** Pre-October-2025 UOM is absent; strict totals are partial, not estimates. Product case pack is not silently substituted for the approved conversion reference.

**Sources:** POS, UOM reference

**Query:** [units.sql](../sql/kpis/units.sql)

## Finance Reconciliation Bridge

Published minus corrected sales = duplicate effect + key-conflict effect + ingest/event-date effect + unexplained residual.

**Grain:** Published week-ending label and channel

**Filters and Exclusions:** Unpublished weeks retain null published values; boundary weeks are flagged partial.

**Proposed Owner:** Finance (proposed)

**Known Limitations:** Week labels are assumed inclusive period ends covering the preceding six days. Generator produces Finance amounts independently, preventing exact proof that those totals came from POS.

**Sources:** POS, legacy Finance report

**Query:** [finance.sql](../sql/kpis/finance.sql)

## Reading-Level Temperature Excursion Rate

Distinct valid readings above 8 C divided by distinct readings with a resolved Celsius temperature. Below 2 C is a separate measure.

**Grain:** Month and telemetry vendor

**Filters and Exclusions:** Exact duplicate readings and null/invalid readings. Vendor inference and firmware corrections are reported.

**Proposed Owner:** Supply Chain (proposed)

**Known Limitations:** UTC-labeled device timestamps follow generator convention after seven-hour correction. This is reading-level, not time-weighted or trip-level. No carrier join exists.

**Sources:** reefer telemetry

**Query:** [cold.sql](../sql/kpis/cold.sql)

## Median Dock Proxy to Dispatch

Median minutes between the sole STAGE scan and sole DISPATCH scan for the same order, warehouse, and local day.

**Grain:** Warehouse across selected dates; eligibility at order/warehouse/day

**Filters and Exclusions:** Missing, repeated, reversed, and cross-day boundaries.

**Proposed Owner:** Warehouse Operations (proposed)

**Known Limitations:** STAGE is an assumed dock proxy. Randomly distributed source scans cannot establish a true shipment journey; eligible coverage is always shown.

**Sources:** WMS, warehouse reference

**Query:** [cycles.sql](../sql/kpis/cycles.sql)

## Outlet Channel Changes

Consecutive source-time outlet versions with differing channels, excluding deletion/recreation transitions.

**Grain:** Outlet and effective change timestamp

**Filters and Exclusions:** Conflicting CDC keys; tie timestamps resolved using greatest sequence.

**Proposed Owner:** Master Data (proposed)

**Known Limitations:** Effective time is source operation time; retroactive business-effective dates are unavailable.

**Sources:** ERP outlet CDC

**Query:** [outlets.sql](../sql/kpis/outlets.sql)

## Comparable Current Order Value

Latest nondeleted order values by source. PARTNER_API comparable value divides recorded gross by 1.085, the generator-confirmed uplift.

**Grain:** Current order grouped by source system and selected order dates

**Filters and Exclusions:** Tombstoned orders and null value fields.

**Proposed Owner:** Finance (proposed)

**Known Limitations:** Adjustment is supported by synthetic generator, not invoice evidence; keep raw value beside it. Source attributes can change across updates. Delete timestamp exceptions are counted.

**Sources:** ERP sales order CDC

**Query:** [orders.sql](../sql/kpis/orders.sql)

## Feed Completeness

Expected and observed file counts, readable row counts, bytes, and row rejections per partition.

**Grain:** Feed and partition

**Filters and Exclusions:** None; rejected files remain visible.

**Proposed Owner:** Data Engineering (proposed)

**Known Limitations:** Manifest covers only POS, telemetry, and WMS. ERP partitions without a manifest show NO_MANIFEST, not certified completeness. Row totals do not prove upstream event delivery.

**Sources:** all feeds, manifest, fiscal calendar, ingestion audit

**Query:** [completeness.sql](../sql/kpis/completeness.sql)

## Gateway Activity Gaps

Zero observed readings between each gateway's first and last observed dates, using a calendar grid.

**Grain:** Gateway and day

**Filters and Exclusions:** Days outside the observed active period.

**Proposed Owner:** Fleet Operations (proposed)

**Known Limitations:** Silence is a candidate outage; cannot infer activation/deactivation or expected sampling frequency. Incomplete partitions are identified separately.

**Sources:** telemetry, fiscal calendar, partition audit

**Query:** [gateway.sql](../sql/kpis/gateway.sql)

## Advisory Sales Anomalies

Daily sales more than three sample standard deviations from prior 28 calendar days, with at least 14 observed baseline days.

**Grain:** Channel and business date

**Filters and Exclusions:** Insufficient history and zero-variance baselines.

**Proposed Owner:** Commercial Analytics (proposed)

**Known Limitations:** Advisory flags only; no automatic exclusions. Not seasonality-aware; incomplete feeds may explain flags. Rule requires business calibration before alerting.

**Sources:** normalized POS

**Query:** [anomalies.sql](../sql/kpis/anomalies.sql)

## Sales Row Trace

Canonical sales line, original source quantity/unit/price, normalized measures, source file, one-based row number, payload hash, and applied schema.

**Grain:** Transaction line

**Filters and Exclusions:** Rejected/conflicting records are available through separate quality records.

**Proposed Owner:** Data Engineering (proposed)

**Known Limitations:** A representative source row is retained for exact duplicates; original files must remain available. No fabricated lineage to Finance's independently generated totals.

**Sources:** POS, ingestion provenance

**Query:** [trace.sql](../sql/kpis/trace.sql)

## Trip Excursions by Carrier

Would require breached chilled trips divided by observed eligible chilled trips.

**Grain:** Month and carrier

**Filters and Exclusions:** Undefined until trip boundaries and joins are supplied.

**Proposed Owner:** Supply Chain (proposed)

**Known Limitations:** Unavailable: no trip ID, chilled-trip population, or defensible carrier mapping in supplied feeds.

**Sources:** telemetry, missing trip/carrier mapping

**Query:** Unavailable with supplied evidence

## On-Time Delivery Service Level

Would require actual delivery completion against requested delivery time and agreed eligibility.

**Grain:** Eligible order

**Filters and Exclusions:** Undefined until delivery evidence is supplied.

**Proposed Owner:** Supply Chain (proposed)

**Known Limitations:** Unavailable: requested date and order status do not provide a reliable actual delivery timestamp. Generated update steps never reach DELIVERED.

**Sources:** ERP orders, missing delivery completion evidence

**Query:** Unavailable with supplied evidence
