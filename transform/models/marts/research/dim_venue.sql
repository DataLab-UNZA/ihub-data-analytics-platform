-- One row per venue (journal, repository or conference), plus one "Unknown venue" row
-- for publications whose source gives no venue. OpenAlex venues are keyed on the OpenAlex
-- source ID; UNZA's OJS journals on "ojs:" plus the journal's path (see
-- int_publications__source_records), because OJS gives no source ID.

with venues as (

    select
        venue_id,
        arg_max(venue_name, n_source_records) filter (where venue_name is not null) as venue_name
    from {{ ref('int_publications__deduplicated') }}
    where venue_id is not null
    group by venue_id

)

select
    md5('venue:' || venue_id) as venue_key,
    venue_id,
    coalesce(
        venue_name,
        case
            when venue_id like 'ojs:%' then 'OJS journal ' || substr(venue_id, 5)
            else venue_id
        end
    ) as venue_name
from venues

union all

select
    md5('venue:unknown') as venue_key,
    cast(null as varchar) as venue_id,
    'Unknown venue' as venue_name
