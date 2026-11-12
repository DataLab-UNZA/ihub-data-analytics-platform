-- One row per OpenAlex work, author, institution and the raw affiliation text that named
-- that institution. An author with no institution has no rows; an institution OpenAlex
-- gives no raw text for has one row with a null raw_affiliation_string. No joins across
-- sources.
--
-- is_unza_institution recognises UNZA by the OpenAlex ID or ROR in the
-- unza_openalex_institution_ids and unza_org_identifiers variables (dbt_project.yml).

with latest as (

    {{ latest_delivery(source('raw_openalex', 'records')) }}

),

-- Lists first, unnest after, at each level (see stg_orcid__works for why).
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

authorship_parts as (

    select
        openalex_id,
        author_position,
        {{ json_list('authorship', '$.institutions') }} as institutions,
        {{ json_list('authorship', '$.affiliations') }} as affiliations
    from authorships

),

institutions as (

    select openalex_id, author_position, unnest(institutions) as institution
    from authorship_parts

),

institution_fields as (

    select
        openalex_id,
        author_position,
        replace(institution ->> '$.id', 'https://openalex.org/', '') as institution_id,
        {{ clean_text("institution ->> '$.display_name'") }} as institution_name,
        institution ->> '$.ror' as institution_ror,
        institution ->> '$.country_code' as country_code,
        institution ->> '$.type' as institution_type
    from institutions

),

affiliations as (

    select openalex_id, author_position, unnest(affiliations) as affiliation
    from authorship_parts

),

affiliation_id_lists as (

    select
        openalex_id,
        author_position,
        {{ clean_text("affiliation ->> '$.raw_affiliation_string'") }} as raw_affiliation_string,
        {{ json_text_list('affiliation', '$.institution_ids') }} as institution_urls
    from affiliations

),

affiliation_institutions as (

    select
        openalex_id,
        author_position,
        raw_affiliation_string,
        unnest(institution_urls) as institution_url
    from affiliation_id_lists

)

select
    institution_fields.openalex_id,
    institution_fields.author_position,
    institution_fields.institution_id,
    institution_fields.institution_name,
    institution_fields.institution_ror,
    institution_fields.country_code,
    institution_fields.institution_type,
    (
        institution_fields.institution_id in (
            {%- for id in var('unza_openalex_institution_ids') %}
            '{{ id }}'{% if not loop.last %},{% endif %}
            {%- endfor %}
        )
        or institution_fields.institution_ror in (
            {%- for identifier in var('unza_org_identifiers') %}
            '{{ identifier }}'{% if not loop.last %},{% endif %}
            {%- endfor %}
        )
    ) is true as is_unza_institution,
    affiliation_institutions.raw_affiliation_string
from institution_fields
left join affiliation_institutions
    on institution_fields.openalex_id = affiliation_institutions.openalex_id
    and institution_fields.author_position = affiliation_institutions.author_position
    and institution_fields.institution_id
        = replace(affiliation_institutions.institution_url, 'https://openalex.org/', '')
