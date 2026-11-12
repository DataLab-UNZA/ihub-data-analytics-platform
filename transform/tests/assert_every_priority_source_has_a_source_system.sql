-- Fails for any source named in the source_priority variable that has no row in the
-- source_systems seed (and so would have no row in dim_source_system).

select source_system
from (
    select unnest([
        {% for source in var('source_priority') %}'{{ source }}'{% if not loop.last %}, {% endif %}{% endfor %}
    ]) as source_system
)
where source_system not in (select source_system from {{ ref('source_systems') }})
