-- One row per publication record from every source, in one common shape, with the
-- publication_key it resolves to. Nothing is dropped except records the source has
-- deleted: this is the link back to each source record.
--
-- To add a source: add one CTE below that selects the same columns from that source's
-- staging model, add it to `unioned`, and add the source to the `source_priority`
-- variable in dbt_project.yml.
--
-- Sources with no open-access data (IRIMS, OJS, ORCID) say is_oa = false and
-- oa_status = null; the mart shows that as "unknown". ORCID works carry no author names.
--
-- Matching (see docs/ROADMAP.md):
--   1. DOI: records with the same normalised DOI are one publication.
--   2. Records without a DOI join a DOI publication when their normalised title + year
--      points to exactly one DOI. The first-author surname is compared only when both
--      records have one (match_rule title_year_to_doi).
--   3. Remaining records with the same normalised title + year + first-author surname are
--      one publication. A record with no surname joins the only surname group of its
--      title + year, or else groups with other nameless records (match_rule title_year).
--   4. Anything else stays a publication of its own (single_record).

with openalex as (

    select
        'openalex' as source_system,
        works.openalex_id as source_record_id,
        'https://openalex.org/' || works.openalex_id as source_url,
        works.doi,
        works.title,
        works.year,
        works.type,
        works.venue_id,
        works.venue_name,
        works.is_oa,
        works.oa_status,
        works.cited_by_count,
        works.n_authors,
        authors.family_name_normalised as first_author_surname,
        works.fetched_at
    from {{ ref('stg_openalex__works') }} as works
    left join {{ ref('stg_openalex__work_authors') }} as authors
        on works.openalex_id = authors.openalex_id
        and authors.author_position = 1

),

dspace as (

    select
        'dspace_oai' as source_system,
        dspace_item_id as source_record_id,
        item_url as source_url,
        doi,
        title,
        year,
        type,
        cast(null as varchar) as venue_id,
        cast(null as varchar) as venue_name,
        false as is_oa,
        cast(null as varchar) as oa_status,
        0 as cited_by_count,
        coalesce(n_authors, 0) as n_authors,
        {{ normalise_title('first_author_family_name') }} as first_author_surname,
        fetched_at
    from {{ ref('stg_dspace_oai__items') }}
    where not is_deleted

),

ojs as (

    select
        'ojs' as source_system,
        ojs_article_id as source_record_id,
        article_url as source_url,
        doi,
        title,
        year,
        type,
        cast(null as varchar) as venue_id,
        venue_name,
        false as is_oa,
        cast(null as varchar) as oa_status,
        0 as cited_by_count,
        coalesce(n_authors, 0) as n_authors,
        {{ normalise_title('first_author_family_name') }} as first_author_surname,
        fetched_at
    from {{ ref('stg_ojs__articles') }}
    where not is_deleted

),

orcid as (

    select
        'orcid' as source_system,
        orcid_work_id as source_record_id,
        work_url as source_url,
        doi,
        title,
        year,
        type,
        cast(null as varchar) as venue_id,
        journal_title as venue_name,
        false as is_oa,
        cast(null as varchar) as oa_status,
        0 as cited_by_count,
        0 as n_authors,
        cast(null as varchar) as first_author_surname,
        fetched_at
    from {{ ref('stg_orcid__works') }}

),

unioned as (

    select * from openalex
    union all
    select * from dspace
    union all
    select * from ojs
    union all
    select * from orcid

),

normalised as (

    select
        *,
        -- lower case, accents removed, anything but letters and digits becomes one space
        {{ normalise_title('title') }} as title_normalised
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

-- Records without a DOI that match the title + year of exactly one DOI (surname compared
-- only when both sides have one).
doi_candidates as (

    select
        r.source_system,
        r.source_record_id,
        min(d.doi) as doi
    from keyed as r
    inner join keyed as d
        on r.doi is null
        and d.doi is not null
        and r.title_year_key = d.title_year_key
        and (
            r.first_author_surname is null
            or d.first_author_surname is null
            or r.first_author_surname = d.first_author_surname
        )
    group by r.source_system, r.source_record_id
    having count(distinct d.doi) = 1

),

with_candidate as (

    select
        keyed.*,
        doi_candidates.doi as candidate_doi
    from keyed
    left join doi_candidates
        on keyed.source_system = doi_candidates.source_system
        and keyed.source_record_id = doi_candidates.source_record_id

),

-- Title + year combinations with exactly one surname among the records still unmatched.
surname_by_title_year as (

    select
        title_year_key,
        min(first_author_surname) as surname
    from with_candidate
    where doi is null
      and candidate_doi is null
      and first_author_surname is not null
      and title_year_key is not null
    group by title_year_key
    having count(distinct first_author_surname) = 1

),

resolved as (

    select
        with_candidate.*,
        surname_by_title_year.surname as only_surname,
        case
            when with_candidate.doi is not null then 'doi'
            when with_candidate.candidate_doi is not null then 'title_year_to_doi'
            when with_candidate.title_year_key is not null then 'title_year'
            else 'single_record'
        end as match_rule,
        case
            when with_candidate.doi is not null
                then 'doi:' || with_candidate.doi
            when with_candidate.candidate_doi is not null
                then 'doi:' || with_candidate.candidate_doi
            when with_candidate.title_year_key is not null
                and with_candidate.first_author_surname is not null
                then 'title:' || with_candidate.title_year_key
                    || '|' || with_candidate.first_author_surname
            when with_candidate.title_year_key is not null
                and surname_by_title_year.surname is not null
                then 'title:' || with_candidate.title_year_key
                    || '|' || surname_by_title_year.surname
            when with_candidate.title_year_key is not null
                then 'title:' || with_candidate.title_year_key
            else 'record:' || with_candidate.source_system
                || ':' || with_candidate.source_record_id
        end as match_basis
    from with_candidate
    left join surname_by_title_year
        on with_candidate.first_author_surname is null
        and with_candidate.title_year_key = surname_by_title_year.title_year_key

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
    first_author_surname,
    fetched_at
from resolved
