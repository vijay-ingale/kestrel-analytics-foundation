select channel,sum(units_eaches) as confirmed_units_eaches,sum(sales_lines) as sales_lines,
       sum(units_eligible_lines) as units_eligible_lines,
       round(100.0 * sum(units_eligible_lines) / nullif(sum(sales_lines),0),2) as coverage_pct,
       sum(missing_uom_lines) as missing_uom_lines,sum(missing_conversion_lines) as missing_conversion_lines
from analytics.mart_sales_daily where business_date between %(start)s and %(end)s
  and (%(channel)s = '' or channel = %(channel)s)
  and (%(warehouse)s = '' or warehouse_code = %(warehouse)s)
group by channel order by channel
