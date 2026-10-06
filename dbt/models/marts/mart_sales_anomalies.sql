with daily as (
    select business_date, channel, sum(gross_sales_inr) as sales from {{ ref('mart_sales_daily') }} group by 1,2
), baseline as (
    select *, count(sales) over w as baseline_days, avg(sales) over w as baseline_mean,
           stddev_samp(sales) over w as baseline_stddev
    from daily window w as (partition by channel order by business_date::timestamp range between interval '28 days' preceding and interval '1 day' preceding)
)
select *, (sales - baseline_mean) / nullif(baseline_stddev,0) as z_score,
       'ADVISORY_3_SIGMA'::text as rule
from baseline where baseline_days >= 14 and baseline_stddev > 0 and abs(sales - baseline_mean) > 3 * baseline_stddev
