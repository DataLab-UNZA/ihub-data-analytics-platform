-- One row per de-duplicated publication. Keys: publication, venue, year, type.
-- n_unza_authors and is_international_collab come from the affiliations OpenAlex gives. For a
-- publication with no OpenAlex affiliation they are null (unknown), never 0 or false:
--   n_unza_authors          authors whose OpenAlex affiliation is UNZA;
--   is_international_collab whether any affiliation is outside Zambia.

with affiliation_measures as (

    select
        publications.publication_key,
        count(distinct authors.author_key) filter (where affiliations.is_unza_institution)
            as n_unza_authors,
        coalesce(
            bool_or(affiliations.country_code is not null and affiliations.country_code <> 'ZM'),
            false
        ) as is_international_collab
    from {{ ref('stg_openalex__work_author_affiliations') }} as affiliations
    inner join {{ ref('int_publications__source_records') }} as publications
        on publications.source_system = 'openalex'
        and publications.source_record_id = affiliations.openalex_id
    inner join {{ ref('int_authors__source_records') }} as authors
        on authors.source_system = 'openalex'
        and authors.source_record_id
            = affiliations.openalex_id || ':' || cast(affiliations.author_position as varchar)
    group by publications.publication_key

)

select
    publication.publication_key,
    md5('venue:' || coalesce(publication.venue_id, 'unknown')) as venue_key,
    publication.year as year_key,
    md5('type:' || coalesce(publication.type, 'unknown')) as type_key,
    publication.cited_by_count,
    publication.n_authors,
    affiliation_measures.n_unza_authors,
    publication.is_oa,
    coalesce(publication.oa_status, 'unknown') as oa_status,
    affiliation_measures.is_international_collab,
    publication.in_openalex,
    publication.in_repository,
    publication.in_ojs
from {{ ref('int_publications__deduplicated') }} as publication
left join affiliation_measures
    on publication.publication_key = affiliation_measures.publication_key
