select source_system,count(*) as orders,count(order_value_gross) as value_eligible_orders,
       sum(order_value_gross) as recorded_order_value_inr,sum(comparable_order_value_inr) as comparable_order_value_inr,
       count(*) filter (where has_generator_supported_adjustment) as adjusted_orders
from analytics.fct_orders where not is_deleted and order_date between %(start)s and %(end)s
  and (%(warehouse)s = '' or warehouse_code = %(warehouse)s)
group by source_system order by source_system
