-- One row per OpenAlex work and author, in the order OpenAlex lists them. Names are split
-- into family and given names so first-author surnames can be matched across sources.
-- No joins across sources.

with latest as (

    {{ latest_delivery(source('raw_openalex', 'records')) }}

),

-- Take the list of authorships first, then unnest it (see stg_orcid__works for why).
authorship_lists as (

    select
        replace(record_id, 'https://openalex.org/', '') as openalex_id,
        {{ json_list('payload', '$.authorships') }} as authorships
    from latest

),

authorships as (

    select
        openalex_id,
        unnest(authorships) as authorship,
        generate_subscripts(authorships, 1) as author_position
    from authorship_lists

),

fields as (

    select
        openalex_id,
        author_position,
        replace(authorship ->> '$.author.id', 'https://openalex.org/', '') as openalex_author_id,
        nullif(
            regexp_extract(
                authorship ->> '$.author.orcid', '([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])', 1
            ),
            ''
        ) as orcid_id,
        {{ clean_text("authorship ->> '$.author.display_name'") }} as author_name,
        authorship ->> '$.author_position' as position_label,
        coalesce(try_cast(authorship ->> '$.is_corresponding' as boolean), false) as is_corresponding
    from authorships

)

select
    openalex_id,
    author_position,
    openalex_author_id,
    orcid_id,
    author_name,
    {{ name_family('author_name') }} as family_name,
    {{ name_given('author_name') }} as given_names,
    {{ normalise_title(name_family('author_name')) }} as family_name_normalised,
    position_label,
    is_corresponding
from fields
