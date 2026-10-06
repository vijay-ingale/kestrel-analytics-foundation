with activity as (
    select gateway_id, reading_date, count(*) as readings from {{ ref('fct_telemetry') }} group by 1,2
), bounds as (
    select gateway_id, min(reading_date) as first_day, max(reading_date) as last_day from activity group by 1
)
select b.gateway_id, c.calendar_date as missing_date,
       case when f.completeness_status = 'COMPLETE' then 'GATEWAY_SILENCE'
            else 'GATEWAY_SILENCE_OR_INCOMPLETE_PARTITION' end as gap_status
from bounds b join {{ source('reference','fiscal_calendar') }} c on c.calendar_date between b.first_day and b.last_day
left join activity a on a.gateway_id = b.gateway_id and a.reading_date = c.calendar_date
left join {{ ref('mart_feed_completeness') }} f on f.feed = 'reefer_telemetry' and f.partition = 'dt=' || c.calendar_date::text
where a.gateway_id is null
