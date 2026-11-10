-- One row per calendar year from the earliest to the latest publication year, with no
-- gaps, so charts show years with no output as zero.

with bounds as (

    select
        min(year) as first_year,
        max(year) as last_year
    from {{ ref('int_publications__deduplicated') }}

)

select
    year as year_key,
    year,
    cast(floor(year / 10) * 10 as integer) as decade_start,
    cast(floor(year / 10) * 10 as varchar) || 's' as decade_label
from bounds, unnest(generate_series(first_year, last_year)) as years(year)
