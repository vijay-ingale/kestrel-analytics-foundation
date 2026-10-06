select * from analytics.mart_feed_completeness
where split_part(partition,'=',2)::date between %(start)s and %(end)s order by feed,partition
