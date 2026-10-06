select * from analytics.mart_sales_anomalies where business_date between %(start)s and %(end)s
  and (%(channel)s = '' or channel = %(channel)s) order by business_date,channel
