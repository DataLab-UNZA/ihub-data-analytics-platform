-- One row per publication, author and organisation: the authorships behind fact_authorship.
--
-- Whose authorships: OpenAlex's, plus the name-only authors of the repository and OJS for a
-- publication with no OpenAlex record (they cannot be matched to OpenAlex authors, so using
-- both would count a person twice). One authorship per publication and author, however many
-- source records carry it.
--
-- The organisations of an authorship (org_basis says which rule gave each row):
--   openalex_institution    an institution other than UNZA that OpenAlex lists for the author;
--   author_department       a UNZA department found for this author (OpenAlex affiliation text,
--                           ORCID employment); used for an author at UNZA;
--   publication_department  otherwise, the department found for the publication (IRIMS sets);
--   unassigned              otherwise "Unassigned department";
--   unknown_organisation    an OpenAlex author with no institution and no department evidence.
-- An author is at UNZA when OpenAlex lists UNZA for them, when a department was found for them,
-- or when they are a name-only author of the repository or OJS.
--
-- Every publication keeps at least one row at UNZA: when none of its authorships is at UNZA, one
-- row with the "No author listed" author carries the department found for the publication, or
-- "Unassigned department".

with openalex_publications as (

    select distinct publication_key
    from {{ ref('int_publications__source_records') }}
    where source_system = 'openalex'

),

authorship_records as (

    select
        publications.publication_key,
        authors.author_key,
        authors.source_system,
        authors.source_record_id,
        authors.author_position,
        coalesce(openalex_authors.is_corresponding, false) as is_corresponding
    from {{ ref('int_authors__source_records') }} as authors
    inner join {{ ref('int_publications__source_records') }} as publications
        on publications.source_system = authors.source_system
        and publications.source_record_id = authors.publication_source_record_id
    left join {{ ref('stg_openalex__work_authors') }} as openalex_authors
        on authors.source_system = 'openalex'
        and openalex_authors.openalex_id = authors.publication_source_record_id
        and openalex_authors.author_position = authors.author_position
    left join openalex_publications
        on openalex_publications.publication_key = publications.publication_key
    where authors.source_system = 'openalex'
        or openalex_publications.publication_key is null

),

authorships as (

    select
        publication_key,
        author_key,
        min(author_position) as author_position,
        bool_or(is_corresponding) as is_corresponding,
        bool_and(source_system <> 'openalex') as is_name_only
    from authorship_records
    group by publication_key, author_key

),

institutions as (

    select distinct
        authorship_records.publication_key,
        authorship_records.author_key,
        affiliations.institution_id,
        affiliations.is_unza_institution
    from {{ ref('stg_openalex__work_author_affiliations') }} as affiliations
    inner join authorship_records
        on authorship_records.source_system = 'openalex'
        and authorship_records.source_record_id
            = affiliations.openalex_id || ':' || cast(affiliations.author_position as varchar)

),

author_departments as (

    select distinct publication_key, author_key, org_unit_id
    from {{ ref('int_publications__departments') }}
    where author_key is not null

),

publication_departments as (

    select distinct publication_key, org_unit_id
    from {{ ref('int_publications__departments') }}
    where author_key is null

),

authorship_status as (

    select
        authorships.*,
        exists (
            select 1 from institutions
            where institutions.publication_key = authorships.publication_key
                and institutions.author_key = authorships.author_key
        ) as has_institution,
        exists (
            select 1 from institutions
            where institutions.publication_key = authorships.publication_key
                and institutions.author_key = authorships.author_key
                and institutions.is_unza_institution
        ) as has_unza_institution,
        exists (
            select 1 from author_departments
            where author_departments.publication_key = authorships.publication_key
                and author_departments.author_key = authorships.author_key
        ) as has_author_department,
        exists (
            select 1 from publication_departments
            where publication_departments.publication_key = authorships.publication_key
        ) as has_publication_department
    from authorships

),

unza_authorships as (

    select *
    from authorship_status
    where has_unza_institution or has_author_department or is_name_only

),

external_rows as (

    select
        publication_key,
        author_key,
        md5('org:openalex:' || institution_id) as org_key,
        'openalex_institution' as org_basis
    from institutions
    where not is_unza_institution

),

unza_rows as (

    select
        unza.publication_key,
        unza.author_key,
        md5('org:' || departments.org_unit_id) as org_key,
        'author_department' as org_basis
    from unza_authorships as unza
    inner join author_departments as departments
        on departments.publication_key = unza.publication_key
        and departments.author_key = unza.author_key

    union all

    select
        unza.publication_key,
        unza.author_key,
        md5('org:' || departments.org_unit_id) as org_key,
        'publication_department' as org_basis
    from unza_authorships as unza
    inner join publication_departments as departments
        on departments.publication_key = unza.publication_key
    where not unza.has_author_department

    union all

    select
        publication_key,
        author_key,
        md5('org:unassigned-department') as org_key,
        'unassigned' as org_basis
    from unza_authorships
    where not has_author_department
        and not has_publication_department

),

unknown_rows as (

    select
        publication_key,
        author_key,
        md5('org:unknown-organisation') as org_key,
        'unknown_organisation' as org_basis
    from authorship_status
    where not has_institution
        and not has_author_department
        and not is_name_only

),

publication_level_rows as (

    select
        publications.publication_key,
        md5('author:none') as author_key,
        md5('org:' || departments.org_unit_id) as org_key,
        'publication_department' as org_basis
    from {{ ref('int_publications__deduplicated') }} as publications
    inner join publication_departments as departments
        on departments.publication_key = publications.publication_key
    where publications.publication_key not in (select publication_key from unza_rows)

    union all

    select
        publications.publication_key,
        md5('author:none') as author_key,
        md5('org:unassigned-department') as org_key,
        'unassigned' as org_basis
    from {{ ref('int_publications__deduplicated') }} as publications
    where publications.publication_key not in (select publication_key from unza_rows)
        and publications.publication_key not in (select publication_key from publication_departments)

),

organisation_rows as (

    select * from external_rows
    union all
    select * from unza_rows
    union all
    select * from unknown_rows
    union all
    select * from publication_level_rows

)

select
    organisation_rows.publication_key,
    organisation_rows.author_key,
    organisation_rows.org_key,
    organisation_rows.org_basis,
    authorships.author_position,
    coalesce(authorships.is_corresponding, false) as is_corresponding
from organisation_rows
left join authorships
    on organisation_rows.publication_key = authorships.publication_key
    and organisation_rows.author_key = authorships.author_key
