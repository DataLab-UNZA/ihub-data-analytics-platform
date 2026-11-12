-- One row per source record, linking it to the de-duplicated publication it belongs to.
-- Nothing is dropped: every live record from every source stays linked, with the rule
-- that matched it. source_system is the source's name (openalex, orcid, dspace_oai, ojs);
-- dim_source_system arrives with the rest of the star schema in issue #20.

select
    publication_key,
    source_system,
    source_record_id,
    source_url,
    match_rule
from {{ ref('int_publications__source_records') }}
