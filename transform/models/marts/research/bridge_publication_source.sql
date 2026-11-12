-- One row per source record, linking it to the de-duplicated publication it belongs to and
-- to its source system. Nothing is dropped: every live record from every source stays
-- linked, with the rule that matched it. A source with no row in dim_source_system gives a
-- null source_system_key, which fails the not_null test: add it to the source_systems seed.

select
    records.publication_key,
    source_systems.source_system_key,
    records.source_record_id,
    records.source_url,
    records.match_rule
from {{ ref('int_publications__source_records') }} as records
left join {{ ref('dim_source_system') }} as source_systems
    on records.source_system = source_systems.source_system
