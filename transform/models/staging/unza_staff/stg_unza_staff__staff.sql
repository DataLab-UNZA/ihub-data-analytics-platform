-- One row per person on the public staff list (ADR-017). Names, title, occupation and
-- school only: the list has no staff ID. Rows without a surname are dropped.

with latest as (

    {{ latest_delivery(source('raw_unza_staff', 'records')) }}

),

tidied as (

    select
        record_id as staff_row_id,
        nullif(trim(regexp_replace(payload ->> '$.Surname', '\s+', ' ', 'g')), '') as surname,
        nullif(trim(regexp_replace(payload ->> '$."First Name"', '\s+', ' ', 'g')), '')
            as first_name,
        nullif(trim(regexp_replace(payload ->> '$."Second Name"', '\s+', ' ', 'g')), '')
            as second_name,
        nullif(trim(regexp_replace(payload ->> '$.Title', '\s+', ' ', 'g')), '') as title,
        nullif(trim(regexp_replace(payload ->> '$.Occupation', '\s+', ' ', 'g')), '')
            as occupation,
        nullif(trim(regexp_replace(payload ->> '$.School', '\s+', ' ', 'g')), '')
            as school_label,
        fetched_at
    from latest

)

select *
from tidied
where surname is not null
