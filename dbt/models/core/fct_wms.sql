select w.*, (w.event_ts at time zone coalesce(d.timezone,'Asia/Kolkata')) as event_ts_utc,
       w.event_ts::date as business_date,
       d.warehouse_code is null as missing_warehouse_reference
from {{ ref('stg_wms') }} w
left join {{ source('reference','warehouse_master') }} d using (warehouse_code)
