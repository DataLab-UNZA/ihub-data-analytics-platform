-- One row per source system (OpenAlex, ORCID, the repository, OJS): the dimension behind
-- bridge_publication_source and the Source coverage page.

select
    md5('source:' || source_system) as source_system_key,
    source_system,
    source_name,
    source_kind,
    description
from {{ ref('source_systems') }}
