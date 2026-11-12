-- One row per OpenAlex topic, with its domain, field and subfield on the same row.
-- Topics come from OpenAlex only; the other sources give no comparable classification.

select
    md5('topic:' || topic_id) as topic_key,
    topic_id,
    min(topic_name) as topic_name,
    min(subfield_id) as subfield_id,
    min(subfield_name) as subfield_name,
    min(field_id) as field_id,
    min(field_name) as field_name,
    min(domain_id) as domain_id,
    min(domain_name) as domain_name
from {{ ref('stg_openalex__work_topics') }}
group by topic_id
