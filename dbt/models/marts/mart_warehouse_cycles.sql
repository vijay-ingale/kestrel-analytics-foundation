with pairs as (
    select order_number, warehouse_code, business_date,
           min(event_ts) filter (where event_type = 'STAGE') as staged_at,
           min(event_ts) filter (where event_type = 'DISPATCH') as dispatched_at,
           count(*) filter (where event_type = 'STAGE') as stage_scans,
           count(*) filter (where event_type = 'DISPATCH') as dispatch_scans
    from {{ ref('fct_wms') }} group by 1,2,3
)
select *, case when staged_at is null or dispatched_at is null then 'MISSING_BOUNDARY'
               when dispatched_at < staged_at then 'NEGATIVE_DURATION'
               when stage_scans <> 1 or dispatch_scans <> 1 then 'AMBIGUOUS_BOUNDARY'
               else 'ELIGIBLE' end as cycle_status,
       case when dispatched_at >= staged_at and stage_scans = 1 and dispatch_scans = 1
            then extract(epoch from dispatched_at - staged_at) / 60 end as cycle_minutes
from pairs
