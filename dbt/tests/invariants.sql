select 'sales_key_not_unique' as issue from {{ ref('fct_sales') }} group by txn_id,txn_line_no having count(*) > 1
union all
select 'history_overlaps' from {{ ref('dim_outlet_history') }} where valid_to <= valid_from
union all
select 'negative_eligible_cycle' from {{ ref('mart_warehouse_cycles') }} where cycle_status = 'ELIGIBLE' and (cycle_minutes is null or cycle_minutes < 0)
union all
select 'reconciliation_bridge_does_not_balance' from {{ ref('mart_finance_reconciliation') }}
where total_variance is not null and abs(total_variance - duplicate_effect - conflict_effect - date_effect - unexplained_residual) > 0.01
union all
select 'excursions_exceed_valid_readings' from {{ ref('mart_cold_chain_daily') }} where excursion_readings > valid_readings
union all
select 'unit_coverage_exceeds_lines' from {{ ref('mart_sales_daily') }} where units_eligible_lines > sales_lines
