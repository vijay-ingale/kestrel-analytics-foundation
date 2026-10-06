select warehouse_code,count(*) as order_warehouse_days,count(cycle_minutes) as eligible_cycles,
       round((percentile_cont(0.5) within group (order by cycle_minutes))::numeric,2) as median_cycle_minutes,
       round(100.0 * count(cycle_minutes) / nullif(count(*),0),4) as coverage_pct,
       count(*) filter (where cycle_status = 'NEGATIVE_DURATION') as reversed_cycles,
       count(*) filter (where cycle_status = 'AMBIGUOUS_BOUNDARY') as ambiguous_cycles
from analytics.mart_warehouse_cycles where business_date between %(start)s and %(end)s
  and (%(warehouse)s = '' or warehouse_code = %(warehouse)s)
group by warehouse_code order by warehouse_code
