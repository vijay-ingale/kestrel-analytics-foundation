select * from analytics.mart_finance_reconciliation
where week_ending between %(start)s and %(end)s and (%(channel)s = '' or channel = %(channel)s)
order by week_ending,channel
