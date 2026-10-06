select reading_date, warehouse_code, telemetry_vendor,
       count(*) as readings, count(temperature_c) as valid_readings,
       count(*) filter (where is_excursion) as excursion_readings,
       count(*) filter (where is_below_band) as below_band_readings,
       count(*) filter (where unit_resolution_method <> 'EXPLICIT') as inferred_unit_readings,
       count(*) filter (where firmware_version = '2.1.4') as corrected_clock_readings,
       count(*) filter (where temperature_c is null) as missing_temperature_readings
from {{ ref('fct_telemetry') }} group by 1,2,3
