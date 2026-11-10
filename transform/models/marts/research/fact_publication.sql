-- One row per de-duplicated publication. Keys: publication, venue, year, type.
-- Not yet available (need authorships, issue #20): n_unza_authors, is_international_collab.
-- in_repository and in_ojs stay false until those sources are loaded.

select
    publication.publication_key,
    md5('venue:' || coalesce(publication.venue_id, 'unknown')) as venue_key,
    publication.year as year_key,
    md5('type:' || coalesce(publication.type, 'unknown')) as type_key,
    publication.cited_by_count,
    publication.n_authors,
    publication.is_oa,
    coalesce(publication.oa_status, 'unknown') as oa_status,
    publication.in_openalex,
    publication.in_repository,
    publication.in_ojs
from {{ ref('int_publications__deduplicated') }} as publication
