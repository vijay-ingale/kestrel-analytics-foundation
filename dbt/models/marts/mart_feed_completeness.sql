with observed as (
    select feed, partition, count(*) as observed_files, sum(observed_rows) as observed_rows,
           sum(accepted_rows) as accepted_rows, sum(rejected_rows) as rejected_rows,
           sum(bytes) as observed_bytes, count(*) filter (where status <> 'OK') as unreadable_files
    from {{ source('audit','files') }} where run_id = (select max(run_id) from {{ source('audit','files') }})
    group by 1,2
), expected as (
    select * from {{ source('reference','expected_partitions') }}
), keys as (
    select feed, partition from expected union select feed, partition from observed
    union
    select f.feed, f.part_key || '=' || c.calendar_date::text
    from (values ('pos_transactions','ingest_date'), ('reefer_telemetry','dt'), ('wms_scan_events','dt')) f(feed,part_key)
    cross join {{ source('reference','fiscal_calendar') }} c
)
select k.*, e.file_count as expected_files, e.row_count as expected_rows, e.bytes as expected_bytes,
       coalesce(o.observed_files,0) as observed_files, coalesce(o.observed_rows,0) as observed_rows,
       coalesce(o.accepted_rows,0) as accepted_rows, coalesce(o.rejected_rows,0) as rejected_rows,
       o.observed_bytes, coalesce(o.unreadable_files,0) as unreadable_files,
       case when o.feed is null then 'MISSING_PARTITION'
            when o.unreadable_files > 0 then 'UNREADABLE_FILE'
            when e.feed is null then 'NO_MANIFEST'
            when e.file_count <> o.observed_files or e.row_count <> o.observed_rows or e.bytes <> o.observed_bytes then 'MANIFEST_MISMATCH'
            when o.rejected_rows > 0 then 'ROW_REJECTIONS' else 'COMPLETE' end as completeness_status
from keys k left join expected e using (feed,partition) left join observed o using (feed,partition)
