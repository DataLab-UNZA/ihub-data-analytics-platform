-- One row per publication, author and organisation (affiliation). Keys: publication, author,
-- org, year. An author with two affiliations on a publication has two rows, so count authors
-- with count(distinct author_key). Which authorships and organisations are used, and how a
-- department is found, is set out in int_authorships__resolved.

select
    authorships.publication_key,
    authorships.author_key,
    authorships.org_key,
    publications.year as year_key,
    authorships.author_position,
    authorships.is_corresponding,
    authorships.org_basis
from {{ ref('int_authorships__resolved') }} as authorships
inner join {{ ref('int_publications__deduplicated') }} as publications
    on authorships.publication_key = publications.publication_key
