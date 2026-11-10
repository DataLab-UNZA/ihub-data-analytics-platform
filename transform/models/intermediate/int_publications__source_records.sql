-- One row per publication record from every source, in one common shape, with the
-- publication_key it resolves to. Nothing is dropped: this is the link back to each
-- source record.
--
-- To add a source (ORCID, IRIM, OJS): add one CTE below that selects the same columns
-- from that source's staging model, add it to `unioned`, and add the source to the
-- `source_priority` variable in dbt_project.yml.
--
-- Matching (see docs/ROADMAP.md):
--   1. DOI: records with the same normalised DOI are one publication.
--   2. Normalised title + year: records without a DOI join a DOI publication only when
--      that title + year points to exactly one DOI (so we never guess between two
--      publications); otherwise records with the same title + year are one publication.
--   3. Anything else stays a publication of its own.

with openalex as (

    select
        'openalex' as source_system,
        openalex_id as source_record_id,
        'https://openalex.org/' || openalex_id as source_url,
        doi,
        title,
        year,
        type,
        venue_id,
        venue_name,
        is_oa,
        oa_status,
        cited_by_count,
        n_authors,
        fetched_at
    from {{ ref('stg_openalex__works') }}

),

unioned as (

    select * from openalex
    -- union all select * from orcid
    -- union all select * from dspace
    -- union all select * from ojs

),

normalised as (

    select
        *,
        -- lower case, accents removed, anything but letters and digits becomes one space
        nullif(
            trim(regexp_replace(strip_accents(lower(title)), '[^a-z0-9]+', ' ', 'g')),
            ''
        ) as title_normalised
    from unioned

),

keyed as (

    select
        *,
        case
            when title_normalised is not null and year is not null
                then title_normalised || '|' || cast(year as varchar)
        end as title_year_key
    from normalised

),

-- Title + year combinations that belong to exactly one DOI.
doi_by_title_year as (

    select
        title_year_key,
        min(doi) as doi
    from keyed
    where doi is not null
      and title_year_key is not null
    group by title_year_key
    having count(distinct doi) = 1

),

resolved as (

    select
        keyed.*,
        case
            when keyed.doi is not null then 'doi'
            when doi_by_title_year.doi is not null then 'title_year_to_doi'
            when keyed.title_year_key is not null then 'title_year'
            else 'single_record'
        end as match_rule,
        case
            when keyed.doi is not null then 'doi:' || keyed.doi
            when doi_by_title_year.doi is not null then 'doi:' || doi_by_title_year.doi
            when keyed.title_year_key is not null then 'title:' || keyed.title_year_key
            else 'record:' || keyed.source_system || ':' || keyed.source_record_id
        end as match_basis
    from keyed
    left join doi_by_title_year
        on keyed.doi is null
        and keyed.title_year_key = doi_by_title_year.title_year_key

)

select
    md5(match_basis) as publication_key,
    match_rule,
    source_system,
    source_record_id,
    source_url,
    doi,
    title,
    title_normalised,
    year,
    type,
    venue_id,
    venue_name,
    is_oa,
    oa_status,
    cited_by_count,
    n_authors,
    fetched_at
from resolved
