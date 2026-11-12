-- One row per organisation: UNZA's own units (the hierarchy institution > school >
-- department from the unza_org_units seed), an "Unassigned department" row for publications
-- no department can be found for, and the other institutions OpenAlex lists on authorships.
-- Only UNZA units have a parent: org_kind tells the two apart.

with units as (

    select * from {{ ref('unza_org_units') }}

),

unza_units as (

    select
        md5('org:' || units.org_unit_id) as org_key,
        units.org_unit_id as org_id,
        units.org_unit_name as org_name,
        'unza_unit' as org_kind,
        units.org_unit_type as org_type,
        case
            when units.parent_org_unit_id is not null
                then md5('org:' || units.parent_org_unit_id)
        end as parent_org_key,
        case
            when units.org_unit_type = 'school' then units.org_unit_name
            else schools.org_unit_name
        end as school_name,
        'ZM' as country_code,
        cast(null as varchar) as ror
    from units
    left join units as schools
        on units.parent_org_unit_id = schools.org_unit_id
        and schools.org_unit_type = 'school'

),

unassigned as (

    select
        md5('org:unassigned-department') as org_key,
        'unassigned-department' as org_id,
        'Unassigned department' as org_name,
        'unza_unit' as org_kind,
        'unassigned' as org_type,
        (select md5('org:' || org_unit_id) from units where org_unit_type = 'institution')
            as parent_org_key,
        cast(null as varchar) as school_name,
        'ZM' as country_code,
        cast(null as varchar) as ror

),

external_institutions as (

    select
        md5('org:openalex:' || institution_id) as org_key,
        'openalex:' || institution_id as org_id,
        coalesce(min(institution_name), institution_id) as org_name,
        'external' as org_kind,
        min(institution_type) as org_type,
        cast(null as varchar) as parent_org_key,
        cast(null as varchar) as school_name,
        min(country_code) as country_code,
        min(institution_ror) as ror
    from {{ ref('stg_openalex__work_author_affiliations') }}
    where not is_unza_institution
    group by institution_id

)

select * from unza_units
union all
select * from unassigned
union all
select * from external_institutions
