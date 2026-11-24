-- One row per person on UNZA's public staff list (ADR-017): names, title, occupation and
-- the school label as the list writes it. The Members directory and the school credit read
-- this table when no local roster file is present. There is no staff ID here, by design.

select
    md5(staff_row_id) as staff_key,
    surname,
    first_name,
    second_name,
    title,
    occupation,
    school_label
from {{ ref('stg_unza_staff__staff') }}
