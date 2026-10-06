with tie_resolved as (
    select distinct on (outlet_code, __op_ts) *
    from {{ ref('stg_outlet') }} order by outlet_code, __op_ts, __seq desc
)
select *, __op_ts as valid_from,
       lead(__op_ts) over (partition by outlet_code order by __op_ts) as valid_to,
       __op = 'D' as is_deleted,
       lag(channel) over (partition by outlet_code order by __op_ts) as previous_channel,
       lag(__op) over (partition by outlet_code order by __op_ts) as previous_operation
from tie_resolved
