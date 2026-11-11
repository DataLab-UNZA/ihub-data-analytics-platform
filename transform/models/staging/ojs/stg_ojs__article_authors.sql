-- One row per OJS article and author, in the order the journal lists them. Names are split
-- into family and given names so first-author surnames can be matched across sources.

with authors as (

    select
        ojs_article_id,
        unnest(author_names) as author_name,
        generate_subscripts(author_names, 1) as author_position
    from {{ ref('stg_ojs__articles') }}

)

select
    ojs_article_id,
    author_position,
    author_name,
    {{ name_family('author_name') }} as family_name,
    {{ name_given('author_name') }} as given_names,
    {{ normalise_title(name_family('author_name')) }} as family_name_normalised
from authors
where author_name is not null
