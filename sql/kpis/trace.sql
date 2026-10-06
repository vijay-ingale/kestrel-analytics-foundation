select txn_id,txn_line_no,business_date,channel,historical_outlet_channel,sku_code,
       quantity,uom,unit_price,gross_sales_inr,units_eaches,unit_status,late_arrival,
       _file as source_file,_row as source_row,_hash as payload_hash,_schema_version,_issues
from analytics.fct_sales where txn_id = %(lookup_key)s order by txn_line_no
