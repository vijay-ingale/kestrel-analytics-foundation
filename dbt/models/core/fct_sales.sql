select p.*, (p.event_ts at time zone 'Asia/Kolkata')::date as business_date,
       p.quantity * p.unit_price as gross_sales_inr,
       case when p.quantity is not null and p.unit_price is not null and p.discount_amount is not null
            then p.quantity * p.unit_price - p.discount_amount end as net_sales_inr,
       case when p.uom = 'EA' then p.quantity
            when p.uom = 'CS' then p.quantity * u.eaches_per_case end as units_eaches,
       case when p.uom is null then 'MISSING_SOURCE_UOM'
            when p.quantity is null then 'MISSING_QUANTITY'
            when p.uom = 'CS' and u.eaches_per_case is null then 'MISSING_CONVERSION'
            else 'CONVERTED_OR_EA' end as unit_status,
       coalesce(h.channel, 'UNKNOWN') as historical_outlet_channel,
       coalesce(h.warehouse_code, 'UNKNOWN') as warehouse_code,
       h.outlet_code is null as missing_outlet_reference,
       d.sku_code is null as missing_current_product_reference,
       p._partition > (p.event_ts at time zone 'Asia/Kolkata')::date as late_arrival
from {{ ref('stg_pos') }} p
left join {{ source('reference','uom_conversion') }} u using (sku_code)
left join {{ ref('dim_outlet_history') }} h
  on p.outlet_code = h.outlet_code and p.event_ts >= h.valid_from
 and (h.valid_to is null or p.event_ts < h.valid_to) and not h.is_deleted
left join {{ ref('dim_product') }} d using (sku_code)
