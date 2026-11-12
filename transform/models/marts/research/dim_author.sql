-- One row per de-duplicated author. is_unza_author is true for an author with an OpenAlex
-- authorship that names UNZA, or a UNZA employment on their ORCID record, so Author pages can
-- list UNZA's researchers and leave out their co-authors elsewhere.

with unza_author_keys as (

    select authorships.author_key
    from {{ ref('stg_openalex__work_author_affiliations') }} as affiliations
    inner join {{ ref('int_authors__source_records') }} as authorships
        on authorships.source_system = 'openalex'
        and authorships.source_record_id
            = affiliations.openalex_id || ':' || cast(affiliations.author_position as varchar)
    where affiliations.is_unza_institution

    union

    select researchers.author_key
    from {{ ref('stg_orcid__employments') }} as employments
    inner join {{ ref('int_authors__source_records') }} as researchers
        on researchers.source_system = 'orcid'
        and researchers.source_record_id = employments.orcid_id
    where employments.is_unza

)

select
    authors.author_key,
    coalesce(authors.author_name, 'Unknown author') as author_name,
    authors.orcid_id,
    case when authors.orcid_id is not null then 'https://orcid.org/' || authors.orcid_id end
        as orcid_url,
    authors.openalex_author_id,
    case
        when authors.openalex_author_id is not null
            then 'https://openalex.org/' || authors.openalex_author_id
    end as openalex_url,
    unza_author_keys.author_key is not null as is_unza_author,
    authors.n_source_records,
    authors.n_sources
from {{ ref('int_authors__deduplicated') }} as authors
left join unza_author_keys
    on authors.author_key = unza_author_keys.author_key

union all

-- The author of the row that carries a publication's department when none of its listed
-- authors is at UNZA (see int_authorships__resolved).
select
    md5('author:none') as author_key,
    'No author listed' as author_name,
    cast(null as varchar) as orcid_id,
    cast(null as varchar) as orcid_url,
    cast(null as varchar) as openalex_author_id,
    cast(null as varchar) as openalex_url,
    false as is_unza_author,
    0 as n_source_records,
    0 as n_sources
