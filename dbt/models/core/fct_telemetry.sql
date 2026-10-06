with resolved as (
    select *, case when temp_unit is not null then temp_unit
                   when telemetry_vendor = 'COLDEYE' then 'F'
                   when telemetry_vendor = 'THERMLOG' then 'C' end as resolved_unit,
           reading_ts - case when firmware_version = '2.1.4' then interval '7 hours' else interval '0 hours' end as corrected_ts
    from {{ ref('stg_telemetry') }}
), converted as (
    select *, case when resolved_unit = 'F' then (temp_value - 32) * 5 / 9
                   when resolved_unit = 'C' then temp_value end as temperature_c
    from resolved
)
select *, (corrected_ts at time zone 'UTC')::date as reading_date,
       temperature_c > 8 as is_excursion,
       temperature_c < 2 as is_below_band,
       case when 'UNIT_FROM_COLUMN' = any(_issues) then 'COLUMN'
            when temp_unit is null then 'VENDOR_CONVENTION' else 'EXPLICIT' end as unit_resolution_method
from converted
