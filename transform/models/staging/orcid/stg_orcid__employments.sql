-- One row per employment on a UNZA researcher's ORCID record: organisation, department,
-- role and dates. Department attribution matches department_name against the
-- department_aliases seed for the employments where is_unza is true.
--
-- is_unza recognises UNZA by the organisation identifiers or names in the
-- unza_org_identifiers and unza_org_names variables (dbt_project.yml), so the rule is
-- set in one place.

with latest as (

    {{ latest_delivery(source('raw_orcid', 'records')) }}

),

-- Lists first, unnest after, at each level: unnesting next to a large JSON column copies
-- that column onto every row (see stg_orcid__works).
group_lists as (

    select
        coalesce(payload ->> '$.orcid', record_id) as orcid_id,
        {{ json_list('payload', '$.employments."affiliation-group"') }} as groups,
        fetched_at
    from latest

),

affiliation_groups as (

    select orcid_id, unnest(groups) as affiliation_group, fetched_at
    from group_lists

),

summary_lists as (

    select orcid_id, {{ json_list('affiliation_group', '$.summaries') }} as summaries, fetched_at
    from affiliation_groups

),

summaries as (

    select orcid_id, unnest(summaries) -> '$."employment-summary"' as employment, fetched_at
    from summary_lists

),

fields as (

    select
        orcid_id,
        employment ->> '$."put-code"' as put_code,
        {{ clean_text("employment ->> '$.organization.name'") }} as organisation_name,
        {{ clean_text("employment ->> '$.\"department-name\"'") }} as department_name,
        {{ clean_text("employment ->> '$.\"role-title\"'") }} as role_title,
        try_cast(employment ->> '$."start-date".year.value' as integer) as start_year,
        try_cast(employment ->> '$."start-date".month.value' as integer) as start_month,
        try_cast(employment ->> '$."end-date".year.value' as integer) as end_year,
        try_cast(employment ->> '$."end-date".month.value' as integer) as end_month,
        employment ->> '$.organization.address.city' as city,
        employment ->> '$.organization.address.country' as country_code,
        employment ->> '$.organization."disambiguated-organization"."disambiguated-organization-identifier"'
            as organisation_identifier,
        employment ->> '$.organization."disambiguated-organization"."disambiguation-source"'
            as organisation_identifier_source,
        fetched_at
    from summaries

)

select
    orcid_id || ':' || put_code as orcid_employment_id,
    orcid_id,
    try_cast(put_code as bigint) as put_code,
    organisation_name,
    department_name,
    {{ department_name_key('department_name') }} as department_name_key,
    role_title,
    start_year,
    start_month,
    end_year,
    end_month,
    end_year is null as is_current,
    city,
    country_code,
    organisation_identifier,
    organisation_identifier_source,
    (
        organisation_identifier in (
            {%- for identifier in var('unza_org_identifiers') %}
            '{{ identifier }}'{% if not loop.last %},{% endif %}
            {%- endfor %}
        )
        or {{ normalise_org_name('organisation_name') }} in (
            {%- for name in var('unza_org_names') %}
            '{{ name }}'{% if not loop.last %},{% endif %}
            {%- endfor %}
        )
    ) is true as is_unza,
    fetched_at
from fields
where put_code is not null
