with ranked as (
    select *, row_number() over (partition by sku_code order by __op_ts desc, __seq desc) as rn
    from {{ ref('stg_product') }}
)
select * from ranked where rn = 1 and __op <> 'D'
