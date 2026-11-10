-- One row per de-duplicated publication: the descriptive attributes shown in tables.

select
    publication_key,
    coalesce(title, 'Untitled') as title,
    doi,
    case when doi is not null then 'https://doi.org/' || doi end as doi_url,
    primary_source_system,
    primary_record_url
from {{ ref('int_publications__deduplicated') }}
