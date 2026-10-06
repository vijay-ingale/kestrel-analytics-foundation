select * from analytics.mart_gateway_gaps where missing_date between %(start)s and %(end)s order by missing_date,gateway_id
