-- One row per OpenAlex work and topic, in the order OpenAlex lists them, with the topic's
-- place in OpenAlex's hierarchy (domain > field > subfield > topic). No joins across sources.

with latest as (

    {{ latest_delivery(source('raw_openalex', 'records')) }}

),

-- Take the list of topics first, then unnest it (see stg_orcid__works for why).
topic_lists as (

    select
        replace(record_id, 'https://openalex.org/', '') as openalex_id,
        replace(payload ->> '$.primary_topic.id', 'https://openalex.org/', '') as primary_topic_id,
        {{ json_list('payload', '$.topics') }} as topics
    from latest

),

topics as (

    select
        openalex_id,
        primary_topic_id,
        unnest(topics) as topic,
        generate_subscripts(topics, 1) as topic_rank
    from topic_lists

)

select
    openalex_id,
    topic_rank,
    replace(topic ->> '$.id', 'https://openalex.org/', '') as topic_id,
    {{ clean_text("topic ->> '$.display_name'") }} as topic_name,
    nullif(regexp_extract(topic ->> '$.subfield.id', '([^/]+)$', 1), '') as subfield_id,
    {{ clean_text("topic ->> '$.subfield.display_name'") }} as subfield_name,
    nullif(regexp_extract(topic ->> '$.field.id', '([^/]+)$', 1), '') as field_id,
    {{ clean_text("topic ->> '$.field.display_name'") }} as field_name,
    nullif(regexp_extract(topic ->> '$.domain.id', '([^/]+)$', 1), '') as domain_id,
    {{ clean_text("topic ->> '$.domain.display_name'") }} as domain_name,
    try_cast(topic ->> '$.score' as double) as score,
    coalesce(
        replace(topic ->> '$.id', 'https://openalex.org/', '') = primary_topic_id, false
    ) as is_primary
from topics
