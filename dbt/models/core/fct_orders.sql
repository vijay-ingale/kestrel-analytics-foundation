with ranked as (
    select *, row_number() over (partition by order_number order by __op_ts desc, __seq desc) as rn
    from {{ ref('stg_orders') }}
), tombstones as (
    select order_number, max(__seq) as deletion_seq from {{ ref('stg_orders') }}
    where __op = 'D' group by order_number
)
select r.*, t.deletion_seq,
       (r.__op = 'D' or coalesce(t.deletion_seq >= r.__seq, false)) as is_deleted,
       case when r.source_system = 'PARTNER_API' then r.order_value_gross / 1.085
            else r.order_value_gross end as comparable_order_value_inr,
       r.source_system = 'PARTNER_API' as has_generator_supported_adjustment,
       (t.deletion_seq >= r.__seq and r.__op <> 'D') as deletion_timestamp_exception
from ranked r left join tombstones t using (order_number) where rn = 1
