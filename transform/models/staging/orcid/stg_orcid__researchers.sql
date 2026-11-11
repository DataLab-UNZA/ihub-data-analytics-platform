-- One row per UNZA-affiliated ORCID iD that was harvested, with how many works and
-- employments its public record lists. Authors are matched across sources on this iD first.

with latest as (

    {{ latest_delivery(source('raw_orcid', 'records')) }}

)

select
    coalesce(payload ->> '$.orcid', record_id) as orcid_id,
    'https://orcid.org/' || coalesce(payload ->> '$.orcid', record_id) as orcid_url,
    len({{ json_list('payload', '$.works.group') }}) as n_works,
    len({{ json_list('payload', '$.employments."affiliation-group"') }}) as n_employment_groups,
    fetched_at
from latest
