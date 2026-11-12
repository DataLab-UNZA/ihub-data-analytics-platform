-- One row per de-duplicated author. The name comes from the highest priority source that
-- has one (order set by the `source_priority` variable in dbt_project.yml). Every source
-- record behind an author stays in int_authors__source_records.

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
    from {{ ref('int_authors__source_records') }}

),

ranked as (

    select
        *,
        struct_pack(source_rank := source_rank_only, record_id := source_record_id) as source_rank
    from records

)

select
    author_key,
    max(orcid_id) as orcid_id,
    min(openalex_author_id) as openalex_author_id,
    arg_min(author_name, source_rank) filter (where author_name is not null) as author_name,
    arg_min(family_name_normalised, source_rank)
        filter (where family_name_normalised is not null) as family_name_normalised,
    count(*) as n_source_records,
    count(distinct source_system) as n_sources
from ranked
group by author_key
