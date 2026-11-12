-- The UNZA department-level units (department, centre, library, institute, directorate) each
-- publication is attributed to, with the evidence. One row per publication, author,
-- unit and kind of evidence. A publication with no row is "Unassigned department" in the mart.
--
-- Three kinds of name are matched against the department_aliases seed, as ADR-003 sets out:
--   openalex_affiliation  the parts of the raw affiliation text that names UNZA, for an author
--                         whose institution is UNZA (author-level evidence);
--   orcid_employment      the department of a UNZA employment on the author's ORCID record
--                         that was current in the publication's year (author-level);
--   dspace_set            the names of the IRIMS communities and collections an item sits in
--                         (publication-level: author_key is null).
-- For each name the most specific alias row wins: one for the name's own kind before an
-- "any" row, then one whose school is also named before one without a school. A name that
-- still points to two units is left out rather than guessed. A name that resolves to a school
-- or the institution only gives context, never an attribution. When two matches overlap in
-- the same piece of affiliation text, only the longest is kept.

with alias_keys as (

    select
        aliases.org_unit_id,
        aliases.applies_to,
        aliases.school_context_id,
        {{ department_name_key('aliases.alias') }} as alias_key,
        units.org_unit_type
    from {{ ref('department_aliases') }} as aliases
    inner join {{ ref('unza_org_units') }} as units
        on aliases.org_unit_id = units.org_unit_id

),

-- Every name a school goes by, to tell whether a school is named next to a department.
school_names as (

    select
        org_unit_id as school_id,
        {{ normalise_org_name('org_unit_name') }} as school_name
    from {{ ref('unza_org_units') }}
    where org_unit_type = 'school'

    union

    select
        aliases.org_unit_id as school_id,
        {{ normalise_org_name('aliases.alias') }} as school_name
    from {{ ref('department_aliases') }} as aliases
    inner join {{ ref('unza_org_units') }} as units
        on aliases.org_unit_id = units.org_unit_id
    where units.org_unit_type = 'school'

),

-- Affiliation text is cut at semicolons (separate affiliations) and then at commas, and every
-- run of consecutive parts is a candidate name, up to as many parts as the longest alias has.
-- So "Department of Mathematics, Statistics and Actuarial Science, School of ..." is tried
-- as "Department of Mathematics", "Statistics and Actuarial Science" and as a whole.
-- Unnest next to small columns only (see stg_orcid__works for why).
longest_alias as (

    select max(len(string_split(alias, ','))) as n_parts
    from {{ ref('department_aliases') }}

),

affiliation_chunk_lists as (

    select
        openalex_id,
        author_position,
        raw_affiliation_string,
        string_split(raw_affiliation_string, ';') as chunks
    from {{ ref('stg_openalex__work_author_affiliations') }}
    where is_unza_institution
        and raw_affiliation_string is not null

),

affiliation_chunks as (

    select
        openalex_id,
        author_position,
        raw_affiliation_string,
        unnest(chunks) as chunk,
        generate_subscripts(chunks, 1) as chunk_number
    from affiliation_chunk_lists

),

affiliation_parts as (

    select
        openalex_id,
        author_position,
        raw_affiliation_string,
        chunk_number,
        list_transform(string_split(chunk, ','), lambda part: trim(part)) as parts
    from affiliation_chunks

),

affiliation_starts as (

    select
        openalex_id,
        author_position,
        raw_affiliation_string,
        chunk_number,
        parts,
        unnest(range(1, len(parts) + 1)) as start_position
    from affiliation_parts

),

affiliation_segments as (

    select
        starts.openalex_id,
        starts.author_position,
        starts.raw_affiliation_string,
        starts.chunk_number,
        starts.start_position,
        starts.start_position + lengths.n - 1 as end_position,
        array_to_string(
            list_slice(starts.parts, starts.start_position, starts.start_position + lengths.n - 1),
            ', '
        ) as segment
    from affiliation_starts as starts
    cross join (
        select unnest(range(1, n_parts + 1)) as n from longest_alias
    ) as lengths
    where starts.start_position + lengths.n - 1 <= len(starts.parts)

),

openalex_names as (

    select distinct
        'openalex_affiliation' as evidence,
        'affiliation' as name_kind,
        publications.publication_key,
        authors.author_key,
        segments.openalex_id || ':' || cast(segments.author_position as varchar)
            as source_record_id,
        {{ department_name_key('segments.segment') }} as name_key,
        {{ normalise_org_name('segments.raw_affiliation_string') }} as context,
        trim(segments.segment) as matched_name,
        segments.chunk_number,
        segments.start_position,
        segments.end_position
    from affiliation_segments as segments
    inner join {{ ref('int_publications__source_records') }} as publications
        on publications.source_system = 'openalex'
        and publications.source_record_id = segments.openalex_id
    inner join {{ ref('int_authors__source_records') }} as authors
        on authors.source_system = 'openalex'
        and authors.source_record_id
            = segments.openalex_id || ':' || cast(segments.author_position as varchar)

),

orcid_names as (

    select
        'orcid_employment' as evidence,
        'orcid_employment' as name_kind,
        publications.publication_key,
        authorships.author_key,
        employments.orcid_employment_id as source_record_id,
        employments.department_name_key as name_key,
        {{ normalise_org_name('employments.department_name') }} as context,
        employments.department_name as matched_name,
        cast(null as bigint) as chunk_number,
        cast(null as bigint) as start_position,
        cast(null as bigint) as end_position
    from {{ ref('stg_orcid__employments') }} as employments
    inner join {{ ref('int_authors__source_records') }} as researchers
        on researchers.source_system = 'orcid'
        and researchers.source_record_id = employments.orcid_id
    inner join {{ ref('int_authors__source_records') }} as authorships
        on authorships.author_key = researchers.author_key
        and authorships.publication_source_record_id is not null
    inner join {{ ref('int_publications__source_records') }} as publications
        on publications.source_system = authorships.source_system
        and publications.source_record_id = authorships.publication_source_record_id
    inner join {{ ref('int_publications__deduplicated') }} as deduplicated
        on deduplicated.publication_key = publications.publication_key
    where employments.is_unza
        and employments.department_name_key is not null
        and (employments.start_year is null or employments.start_year <= deduplicated.year)
        and (employments.end_year is null or employments.end_year >= deduplicated.year)

),

item_set_contexts as (

    select
        item_sets.dspace_item_id,
        string_agg({{ normalise_org_name('sets.set_name') }}, ' | ') as context
    from {{ ref('stg_dspace_oai__item_sets') }} as item_sets
    inner join {{ ref('stg_dspace_oai__sets') }} as sets
        on item_sets.set_spec = sets.set_spec
    group by item_sets.dspace_item_id

),

dspace_names as (

    select
        'dspace_set' as evidence,
        'dspace_set' as name_kind,
        publications.publication_key,
        cast(null as varchar) as author_key,
        item_sets.dspace_item_id as source_record_id,
        sets.set_name_key as name_key,
        item_set_contexts.context,
        sets.set_name as matched_name,
        cast(null as bigint) as chunk_number,
        cast(null as bigint) as start_position,
        cast(null as bigint) as end_position
    from {{ ref('stg_dspace_oai__item_sets') }} as item_sets
    inner join {{ ref('stg_dspace_oai__sets') }} as sets
        on item_sets.set_spec = sets.set_spec
    inner join item_set_contexts
        on item_sets.dspace_item_id = item_set_contexts.dspace_item_id
    inner join {{ ref('int_publications__source_records') }} as publications
        on publications.source_system = 'dspace_oai'
        and publications.source_record_id = item_sets.dspace_item_id
    where sets.set_name_key is not null

),

names as (

    select * from openalex_names
    union all
    select * from orcid_names
    union all
    select * from dspace_names

),

candidates as (

    select
        names.*,
        alias_keys.org_unit_id,
        alias_keys.org_unit_type,
        (case when alias_keys.applies_to = names.name_kind then 0 else 2 end)
            + (case when alias_keys.school_context_id is not null then 0 else 1 end)
            as specificity
    from names
    inner join alias_keys
        on alias_keys.alias_key = names.name_key
        and alias_keys.applies_to in (names.name_kind, 'any')
    where alias_keys.school_context_id is null
        or exists (
            select 1
            from school_names
            where school_names.school_id = alias_keys.school_context_id
                and contains(' ' || names.context || ' ', ' ' || school_names.school_name || ' ')
        )

),

best as (

    select *
    from candidates
    qualify specificity = min(specificity) over (
        partition by evidence, publication_key, author_key, source_record_id, matched_name,
            chunk_number, start_position
    )

),

resolved as (

    select
        evidence,
        publication_key,
        author_key,
        source_record_id,
        matched_name,
        chunk_number,
        start_position,
        min(end_position) as end_position,
        min(org_unit_id) as org_unit_id,
        min(org_unit_type) as org_unit_type
    from best
    group by evidence, publication_key, author_key, source_record_id, matched_name,
        chunk_number, start_position
    having count(distinct org_unit_id) = 1

),

department_matches as (

    select *
    from resolved
    where org_unit_type not in ('school', 'institution')

),

-- When two matches overlap in the same piece of affiliation text, only the longest stays:
-- "Mathematics, Statistics and Actuarial Science" must not also count as a shorter name
-- found inside it. Matches of equal length are all kept.
longest_matches as (

    select *
    from department_matches as shorter
    where not exists (
        select 1
        from department_matches as longer
        where longer.evidence = shorter.evidence
            and longer.publication_key = shorter.publication_key
            and longer.author_key is not distinct from shorter.author_key
            and longer.source_record_id = shorter.source_record_id
            and longer.chunk_number = shorter.chunk_number
            and longer.start_position <= shorter.end_position
            and shorter.start_position <= longer.end_position
            and longer.end_position - longer.start_position
                > shorter.end_position - shorter.start_position
    )

)

select
    publication_key,
    author_key,
    org_unit_id,
    evidence,
    min(matched_name) as matched_name
from longest_matches
group by publication_key, author_key, org_unit_id, evidence
