{% macro deduplicate(table, keys=[]) %}
with exact as (
    select distinct on (_hash) *
    from {{ source('raw', table) }}
    order by _hash, _file, _row
)
{% if keys %}
, conflicts as (
    select {{ keys | join(', ') }} from exact
    group by {{ keys | join(', ') }} having count(*) > 1
)
select e.* from exact e
where not exists (
    select 1 from conflicts c where
    {% for key in keys %}c.{{ key }} = e.{{ key }}{% if not loop.last %} and {% endif %}{% endfor %}
)
{% else %}
select * from exact
{% endif %}
{% endmacro %}
