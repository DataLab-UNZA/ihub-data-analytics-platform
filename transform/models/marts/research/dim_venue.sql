-- One row per venue (journal, repository or conference), plus one "Unknown venue" row
-- for publications whose source gives no venue.

with venues as (

    select
        venue_id,
        arg_max(venue_name, n_source_records) as venue_name
    from {{ ref('int_publications__deduplicated') }}
    where venue_id is not null
    group by venue_id

)

select
    md5('venue:' || venue_id) as venue_key,
    venue_id,
    coalesce(venue_name, venue_id) as venue_name
from venues

union all

select
    md5('venue:unknown') as venue_key,
    cast(null as varchar) as venue_id,
    'Unknown venue' as venue_name
