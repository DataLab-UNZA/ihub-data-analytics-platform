-- One row per de-duplicated publication. Descriptive fields come from the highest
-- priority source that has a value (order set by the `source_priority` variable in
-- dbt_project.yml); counts and open-access flags take the most generous source value.
-- Every source record behind a publication stays in int_publications__source_records.

with records as (

    select
        *,
        coalesce(
            list_position(
                [{% for source in var('source_priority') %}'{{ source }}'{% if not loop.last %}, {% endif %}{% endfor %}],
                source_system
            ),
            999
        ) as source_rank_only
    from {{ ref('int_publications__source_records') }}

),

-- Rank by source priority, then by record id so ties always resolve the same way.
ranked as (

    select
        *,
        struct_pack(source_rank := source_rank_only, record_id := source_record_id) as source_rank
    from records

)

select
    publication_key,
    arg_min(doi, source_rank) filter (where doi is not null) as doi,
    arg_min(title, source_rank) filter (where title is not null) as title,
    arg_min(year, source_rank) filter (where year is not null) as year,
    arg_min(type, source_rank) filter (where type is not null) as type,
    arg_min(venue_id, source_rank) filter (where venue_id is not null) as venue_id,
    arg_min(venue_name, source_rank) filter (where venue_name is not null) as venue_name,
    bool_or(is_oa) as is_oa,
    -- Same record as is_oa: the best status among records that are open access, if any.
    coalesce(
        arg_min(oa_status, source_rank) filter (where is_oa and oa_status is not null),
        arg_min(oa_status, source_rank) filter (where oa_status is not null)
    ) as oa_status,
    max(cited_by_count) as cited_by_count,
    max(n_authors) as n_authors,
    arg_min(source_system, source_rank) as primary_source_system,
    arg_min(source_url, source_rank) as primary_record_url,
    count(*) as n_source_records,
    count(distinct source_system) as n_sources,
    bool_or(source_system = 'openalex') as in_openalex,
    bool_or(source_system = 'dspace_oai') as in_repository,
    bool_or(source_system = 'ojs') as in_ojs
from ranked
group by publication_key
