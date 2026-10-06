select channel, sum(gross_sales_inr) as gross_sales_inr, sum(net_sales_inr) as net_sales_inr,
       sum(sales_lines) as sales_lines, sum(revenue_eligible_lines) as revenue_eligible_lines,
       sum(late_lines) as late_lines, sum(unmatched_outlet_lines) as unmatched_outlet_lines
from analytics.mart_sales_daily
where business_date between %(start)s and %(end)s
  and (%(channel)s = '' or channel = %(channel)s)
  and (%(warehouse)s = '' or warehouse_code = %(warehouse)s)
group by channel order by channel
