-- One row per OpenAlex work: renamed, typed and standardised. No joins across sources.
--
-- The raw table keeps every delivery exactly as fetched, and OpenAlex can deliver the
-- same work on two pages of one pull. This model keeps one row per work: the most
-- recently fetched delivery (ties broken on the payload so the choice never changes
-- between builds).

with source as (

    select * from {{ source('raw_openalex', 'records') }}

),

latest_delivery as (

    select *
    from source
    qualify row_number() over (
        partition by record_id
        order by fetched_at desc, md5(cast(payload as varchar))
    ) = 1

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
        coalesce(cast(payload ->> '$.is_xpac' as boolean), false) as is_xpac,
        fetched_at
    from latest_delivery

)

select * from renamed
