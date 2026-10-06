select business_date, channel, warehouse_code,
       sum(gross_sales_inr) as gross_sales_inr, sum(net_sales_inr) as net_sales_inr,
       sum(units_eaches) as units_eaches, count(*) as sales_lines,
       count(gross_sales_inr) as revenue_eligible_lines,
       count(units_eaches) as units_eligible_lines,
       count(*) filter (where late_arrival) as late_lines,
       count(*) filter (where unit_status = 'MISSING_SOURCE_UOM') as missing_uom_lines,
       count(*) filter (where unit_status = 'MISSING_CONVERSION') as missing_conversion_lines,
       count(*) filter (where missing_outlet_reference) as unmatched_outlet_lines
from {{ ref('fct_sales') }} group by 1,2,3
