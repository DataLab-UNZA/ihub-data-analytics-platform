-- One row per author record from every source, with the author_key it resolves to.
--
-- Matching (see docs/ROADMAP.md): ORCID iD first, then OpenAlex author ID.
--   orcid                the record carries an ORCID iD
--   openalex_id_to_orcid the record has an OpenAlex ID that carries exactly one ORCID iD
--                        on other records, so it joins that ORCID group
--   openalex_id          an OpenAlex ID with no ORCID iD anywhere
--   single_record        a name only (IRIMS, OJS): left unmatched, so one person can
--                        appear more than once (decision for issue #19)
-- An ORCID researcher record (stg_orcid__researchers) has an iD but no name.

with openalex as (

    select
        'openalex' as source_system,
        openalex_id || ':' || cast(author_position as varchar) as source_record_id,
        openalex_id as publication_source_record_id,
        author_position,
        author_name,
        family_name_normalised,
        orcid_id,
        openalex_author_id
    from {{ ref('stg_openalex__work_authors') }}

),

dspace as (

    select
        'dspace_oai' as source_system,
        dspace_item_id || ':' || cast(author_position as varchar) as source_record_id,
        dspace_item_id as publication_source_record_id,
        author_position,
        author_name,
        family_name_normalised,
        cast(null as varchar) as orcid_id,
        cast(null as varchar) as openalex_author_id
    from {{ ref('stg_dspace_oai__item_authors') }}
    where dspace_item_id in (
        select dspace_item_id from {{ ref('stg_dspace_oai__items') }} where not is_deleted
    )

),

ojs as (

    select
        'ojs' as source_system,
        ojs_article_id || ':' || cast(author_position as varchar) as source_record_id,
        ojs_article_id as publication_source_record_id,
        author_position,
        author_name,
        family_name_normalised,
        cast(null as varchar) as orcid_id,
        cast(null as varchar) as openalex_author_id
    from {{ ref('stg_ojs__article_authors') }}
    where ojs_article_id in (
        select ojs_article_id from {{ ref('stg_ojs__articles') }} where not is_deleted
    )

),

orcid as (

    select
        'orcid' as source_system,
        orcid_id as source_record_id,
        cast(null as varchar) as publication_source_record_id,
        cast(null as bigint) as author_position,
        cast(null as varchar) as author_name,
        cast(null as varchar) as family_name_normalised,
        orcid_id,
        cast(null as varchar) as openalex_author_id
    from {{ ref('stg_orcid__researchers') }}

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

-- OpenAlex IDs that carry exactly one ORCID iD somewhere (never guess between two).
orcid_by_openalex_id as (

    select
        openalex_author_id,
        min(orcid_id) as orcid_id
    from unioned
    where openalex_author_id is not null
      and orcid_id is not null
    group by openalex_author_id
    having count(distinct orcid_id) = 1

),

resolved as (

    select
        unioned.*,
        case
            when unioned.orcid_id is not null then 'orcid'
            when by_id.orcid_id is not null then 'openalex_id_to_orcid'
            when unioned.openalex_author_id is not null then 'openalex_id'
            else 'single_record'
        end as match_rule,
        case
            when unioned.orcid_id is not null then 'orcid:' || unioned.orcid_id
            when by_id.orcid_id is not null then 'orcid:' || by_id.orcid_id
            when unioned.openalex_author_id is not null
                then 'openalex:' || unioned.openalex_author_id
            else 'record:' || unioned.source_system || ':' || unioned.source_record_id
        end as match_basis
    from unioned
    left join orcid_by_openalex_id as by_id
        on unioned.orcid_id is null
        and unioned.openalex_author_id = by_id.openalex_author_id

)

select
    md5(match_basis) as author_key,
    match_rule,
    source_system,
    source_record_id,
    publication_source_record_id,
    author_position,
    author_name,
    family_name_normalised,
    orcid_id,
    openalex_author_id
from resolved
