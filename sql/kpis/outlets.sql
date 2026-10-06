select outlet_code,previous_channel,channel as new_channel,valid_from,__seq,_file,_row
from analytics.dim_outlet_history
where not is_deleted and previous_operation <> 'D' and previous_channel is not null
  and previous_channel <> channel
  and (valid_from at time zone 'Asia/Kolkata')::date between %(start)s and %(end)s
  and (%(channel)s = '' or channel = %(channel)s)
  and (%(warehouse)s = '' or warehouse_code = %(warehouse)s)
order by valid_from,outlet_code
