-- One row per de-duplicated publication and topic. Several OpenAlex records can sit behind
-- one publication, so their topics are merged: the best score, and primary if any record
-- names the topic as its primary one. Publications OpenAlex gives no topics have no rows.

with openalex_records as (

    select
        source_record_id as openalex_id,
        publication_key
    from {{ ref('int_publications__source_records') }}
    where source_system = 'openalex'

)

select
    openalex_records.publication_key,
    md5('topic:' || topics.topic_id) as topic_key,
    max(topics.score) as score,
    bool_or(topics.is_primary) as is_primary_topic
from {{ ref('stg_openalex__work_topics') }} as topics
inner join openalex_records
    on topics.openalex_id = openalex_records.openalex_id
group by 1, 2
