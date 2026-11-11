-- One row per IRIMS item and author (dc:creator), in the order the repository lists them.
-- Names are split into family and given names so first-author surnames can be matched
-- across sources.

with authors as (

    select
        dspace_item_id,
        unnest(author_names) as author_name,
        generate_subscripts(author_names, 1) as author_position
    from {{ ref('stg_dspace_oai__items') }}

)

select
    dspace_item_id,
    author_position,
    author_name,
    {{ name_family('author_name') }} as family_name,
    {{ name_given('author_name') }} as given_names,
    {{ normalise_title(name_family('author_name')) }} as family_name_normalised
from authors
