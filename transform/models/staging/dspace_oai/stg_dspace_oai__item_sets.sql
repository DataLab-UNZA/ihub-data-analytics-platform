-- One row per IRIMS item and set (community or collection) it belongs to, taken from the
-- item's OAI header. Joined to stg_dspace_oai__sets, this gives each item's community and
-- collection names for department attribution.

select distinct
    dspace_item_id,
    set_spec,
    case
        when starts_with(set_spec, 'com_') then 'community'
        when starts_with(set_spec, 'col_') then 'collection'
        else 'other'
    end as set_kind
from (
    select dspace_item_id, unnest(set_specs) as set_spec
    from {{ ref('stg_dspace_oai__items') }}
)
