with target as (
    select (date_trunc('quarter', %(as_of)s::date)::date - interval '3 months')::date as first_day,
           (date_trunc('quarter', %(as_of)s::date)::date - interval '1 day')::date as last_day
), covered as (
    select t.*, count(c.calendar_date) = last_day - first_day + 1 as full_calendar
    from target t left join reference.fiscal_calendar c on c.calendar_date between t.first_day and t.last_day
    group by t.first_day,t.last_day
)
select c.fiscal_year,c.fiscal_quarter,s.channel,sum(s.gross_sales_inr) as gross_sales_inr,
       t.first_day,t.last_day
from analytics.mart_sales_daily s join reference.fiscal_calendar c on c.calendar_date = s.business_date
cross join covered t
where t.full_calendar and s.business_date between t.first_day and t.last_day
  and (%(channel)s = '' or s.channel = %(channel)s)
  and (%(warehouse)s = '' or s.warehouse_code = %(warehouse)s)
group by 1,2,3,t.first_day,t.last_day order by s.channel
