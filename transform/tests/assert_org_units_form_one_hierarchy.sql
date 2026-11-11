-- Fails for every unit of unza_org_units that breaks the hierarchy
-- institution > school > department (or centre), with the Library, institutes and
-- directorates directly under the institution, and for every alias whose school context
-- is not a school or does not contain the alias's unit.

with units as (

    select * from {{ ref('unza_org_units') }}

),

with_parent as (

    select
        unit.org_unit_id,
        unit.org_unit_type,
        parent.org_unit_type as parent_type
    from units as unit
    left join units as parent
        on parent.org_unit_id = unit.parent_org_unit_id

),

bad_units as (

    select org_unit_id, 'parent is ' || coalesce(parent_type, 'missing') as problem
    from with_parent
    where not (
        (org_unit_type = 'institution' and parent_type is null)
        or (
            org_unit_type in ('school', 'library', 'institute', 'directorate')
            and parent_type = 'institution'
        )
        or (org_unit_type in ('department', 'centre') and parent_type = 'school')
    )

),

aliases as (

    select * from {{ ref('department_aliases') }}

),

bad_contexts as (

    select
        alias.alias || ' -> ' || alias.org_unit_id as org_unit_id,
        'school context ' || alias.school_context_id || ' does not contain the unit' as problem
    from aliases as alias
    left join units as school
        on school.org_unit_id = alias.school_context_id
    left join units as unit
        on unit.org_unit_id = alias.org_unit_id
    where alias.school_context_id is not null
      and (
          school.org_unit_type is distinct from 'school'
          or (
              unit.org_unit_id is distinct from school.org_unit_id
              and unit.parent_org_unit_id is distinct from school.org_unit_id
          )
      )

)

select * from bad_units
union all
select * from bad_contexts
