-- One row per publication type (article, review, book-chapter, ...), plus "unknown".

with types as (

    select distinct coalesce(type, 'unknown') as type_code
    from {{ ref('int_publications__deduplicated') }}

)

select
    md5('type:' || type_code) as type_key,
    type_code,
    upper(left(type_code, 1)) || substr(replace(type_code, '-', ' '), 2) as type_label
from types
