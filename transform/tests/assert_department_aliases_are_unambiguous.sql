-- Fails for every alias that, compared on its matching key (department_name_key), maps to
-- more than one unit for the same kind of name and the same school context, and for any
-- alias that has no key at all. An ambiguous alias could not be resolved; give one of its
-- rows an applies_to or a school_context_id.

with keyed as (

    select
        {{ department_name_key('alias') }} as alias_key,
        alias,
        applies_to,
        school_context_id,
        org_unit_id
    from {{ ref('department_aliases') }}

)

select
    alias_key,
    applies_to,
    school_context_id,
    string_agg(distinct org_unit_id, ', ') as org_unit_ids
from keyed
group by alias_key, applies_to, school_context_id
having count(distinct org_unit_id) > 1 or alias_key is null
