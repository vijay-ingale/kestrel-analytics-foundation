with anchor as (select min(week_ending) as first_end from {{ source('reference','legacy_finance_weekly_report') }}),
raw_values as (
    select first_end + (((_partition - first_end + 6) / 7) * 7) as week_ending, channel,
           sum(quantity * unit_price) as raw_ingest_sales
    from {{ source('raw','pos') }} cross join anchor group by 1,2
), exact as (
    select distinct on (_hash) * from {{ source('raw','pos') }} order by _hash, _file, _row
), dedup_values as (
    select first_end + (((_partition - first_end + 6) / 7) * 7) as week_ending, channel,
           sum(quantity * unit_price) as dedup_ingest_sales
    from exact cross join anchor group by 1,2
), valid_values as (
    select first_end + (((_partition - first_end + 6) / 7) * 7) as week_ending, channel,
           sum(quantity * unit_price) as valid_ingest_sales
    from {{ ref('stg_pos') }} cross join anchor group by 1,2
), corrected as (
    select first_end + (((business_date - first_end + 6) / 7) * 7) as week_ending, channel,
           sum(gross_sales_inr) as corrected_event_sales
    from {{ ref('fct_sales') }} cross join anchor group by 1,2
), keys as (
    select week_ending, channel from raw_values union select week_ending, channel from corrected
    union select week_ending, channel from {{ source('reference','legacy_finance_weekly_report') }}
)
select k.*, p.gross_sales_inr as published_sales,
       coalesce(r.raw_ingest_sales,0) as raw_ingest_sales,
       coalesce(d.dedup_ingest_sales,0) as dedup_ingest_sales,
       coalesce(v.valid_ingest_sales,0) as valid_ingest_sales,
       coalesce(c.corrected_event_sales,0) as corrected_event_sales,
       coalesce(r.raw_ingest_sales,0) - coalesce(d.dedup_ingest_sales,0) as duplicate_effect,
       coalesce(d.dedup_ingest_sales,0) - coalesce(v.valid_ingest_sales,0) as conflict_effect,
       coalesce(v.valid_ingest_sales,0) - coalesce(c.corrected_event_sales,0) as date_effect,
       p.gross_sales_inr - coalesce(r.raw_ingest_sales,0) as unexplained_residual,
       p.gross_sales_inr - coalesce(c.corrected_event_sales,0) as total_variance,
       k.week_ending - 6 < (select min(calendar_date) from {{ source('reference','fiscal_calendar') }})
       or k.week_ending > (select max(calendar_date) from {{ source('reference','fiscal_calendar') }}) as partial_week
from keys k left join raw_values r using (week_ending,channel)
left join dedup_values d using (week_ending,channel)
left join valid_values v using (week_ending,channel)
left join corrected c using (week_ending,channel)
left join {{ source('reference','legacy_finance_weekly_report') }} p using (week_ending,channel)
