{% for table, keys in [('pos',['txn_id','txn_line_no']),('wms',['scan_id']),('outlet',['outlet_code','__op_ts','__seq']),('product',['sku_code','__op_ts','__seq']),('orders',['order_number','__op_ts','__seq'])] %}
select '{{ table }}'::text as source_table,
       concat_ws('|', {% for key in keys %}{{ key }}::text{% if not loop.last %}, {% endif %}{% endfor %}) as business_key,
       count(*) as raw_rows, count(distinct _hash) as distinct_payloads,
       min(_file) as sample_source_file
from {{ source('raw',table) }} group by {{ keys | join(', ') }} having count(distinct _hash) > 1
{% if not loop.last %}union all{% endif %}
{% endfor %}
