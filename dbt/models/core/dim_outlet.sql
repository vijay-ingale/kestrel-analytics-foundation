select * from {{ ref('dim_outlet_history') }} where valid_to is null and not is_deleted
