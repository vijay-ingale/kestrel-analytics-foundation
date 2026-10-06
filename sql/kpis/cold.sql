select date_trunc('month',reading_date)::date as month,telemetry_vendor,
       sum(readings) as readings,sum(valid_readings) as valid_readings,
       sum(excursion_readings) as excursion_readings,
       round(100.0 * sum(excursion_readings) / nullif(sum(valid_readings),0),2) as excursion_rate_pct,
       sum(below_band_readings) as below_band_readings,
       sum(missing_temperature_readings) as missing_temperature_readings,
       sum(inferred_unit_readings) as inferred_unit_readings,sum(corrected_clock_readings) as corrected_clock_readings
from analytics.mart_cold_chain_daily where reading_date between %(start)s and %(end)s
  and (%(warehouse)s = '' or warehouse_code = %(warehouse)s)
group by 1,2 order by 1,2
