-- One row per OpenAlex work: renamed, typed and standardised. No joins across sources.

with source as (

    select * from {{ source('raw_openalex', 'records') }}

),

renamed as (

    select
        replace(record_id, 'https://openalex.org/', '') as openalex_id,
        payload ->> '$.title' as title,
        cast(payload ->> '$.publication_year' as integer) as year,
        payload ->> '$.type' as type,
        replace(
            payload ->> '$.primary_location.source.id', 'https://openalex.org/', ''
        ) as venue_id,
        payload ->> '$.primary_location.source.display_name' as venue_name,
        nullif(
            regexp_replace(
                lower(trim(payload ->> '$.doi')), '^https?://(dx\.)?doi\.org/', ''
            ),
            ''
        ) as doi,
        coalesce(cast(payload ->> '$.open_access.is_oa' as boolean), false) as is_oa,
        payload ->> '$.open_access.oa_status' as oa_status,
        coalesce(cast(payload ->> '$.cited_by_count' as integer), 0) as cited_by_count,
        coalesce(json_array_length(payload -> '$.authorships'), 0) as n_authors,
        fetched_at
    from source

)

select * from renamed
