-- One row per IRIMS (DSpace) set: a community or a collection. Their names are what
-- department attribution matches against the department_aliases seed.

with latest as (

    {{ latest_delivery(source('raw_dspace_oai', 'records'), where="payload ->> '$.record_type' = 'set'") }}

)

select
    payload ->> '$.set_spec' as set_spec,
    case
        when starts_with(payload ->> '$.set_spec', 'com_') then 'community'
        when starts_with(payload ->> '$.set_spec', 'col_') then 'collection'
        else 'other'
    end as set_kind,
    {{ clean_text("payload ->> '$.set_name'") }} as set_name,
    {{ department_name_key("payload ->> '$.set_name'") }} as set_name_key,
    fetched_at
from latest
