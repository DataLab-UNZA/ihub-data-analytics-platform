-- One row per IRIMS (DSpace) item: renamed, typed and standardised. No joins across sources.
--
-- The connector yields an item once for every set it harvests, so the newest delivery of
-- each OAI identifier is kept (latest_delivery). Deleted items stay, flagged with
-- is_deleted, so later layers can tell "removed from the repository" from "never there".
--
-- Dublin Core (oai_dc) gives every element as a list. The rules used here:
--   title   the first dc:title
--   year    the earliest year among dc:date values without a time (the issue date);
--           DSpace's accession timestamps are used only when there is no such value
--   type    the first dc:type, mapped to the shared vocabulary (standardise_publication_type)
--   doi     the first dc:identifier that holds a DOI
--   link    https://<repository host>/handle/<handle>, from the OAI identifier

with latest as (

    {{ latest_delivery(source('raw_dspace_oai', 'records'), where="payload ->> '$.record_type' = 'item'") }}

),

fields as (

    select
        record_id,
        payload ->> '$.datestamp' as datestamp_text,
        {{ json_text_list('payload', '$.set_specs') }} as set_specs,
        coalesce(try_cast(payload ->> '$.deleted' as boolean), false) as is_deleted,
        {{ json_text_list('payload', '$.metadata.title') }} as titles,
        {{ json_text_list('payload', '$.metadata.creator') }} as creators,
        {{ json_text_list('payload', '$.metadata.date') }} as dates,
        {{ json_text_list('payload', '$.metadata.type') }} as types,
        {{ json_text_list('payload', '$.metadata.identifier') }} as identifiers,
        {{ json_text_list('payload', '$.metadata.subject') }} as subjects,
        {{ json_text_list('payload', '$.metadata.language') }} as languages,
        {{ json_text_list('payload', '$.metadata.publisher') }} as publishers,
        fetched_at
    from latest

),

standardised as (

    select
        record_id as dspace_item_id,
        nullif(regexp_extract(record_id, ':([0-9]+/[0-9]+)$', 1), '') as handle,
        -- The item's page, built from its OAI identifier ("oai:<repository host>:<handle>"),
        -- because the handle links in dc:identifier still name the repository's old address
        -- (dspace.unza.zm), which no longer resolves. Falls back to dc:identifier.
        coalesce(
            'https://' || nullif(regexp_extract(record_id, '^oai:([^:]+):', 1), '')
                || '/handle/' || nullif(regexp_extract(record_id, ':([0-9]+/[0-9]+)$', 1), ''),
            list_filter(identifiers, lambda i: i like '%/handle/%')[1]
        ) as item_url,
        {{ clean_text('titles[1]') }} as title,
        coalesce(
            list_min(list_transform(
                list_filter(dates, lambda d: not contains(d, 'T')),
                lambda d: {{ year_from_text('d') }}
            )),
            list_min(list_transform(dates, lambda d: {{ year_from_text('d') }}))
        ) as year,
        {{ standardise_publication_type('types[1]') }} as type,
        types[1] as source_type,
        list_filter(
            list_transform(identifiers, lambda i: {{ normalise_doi('i') }}),
            lambda d: d is not null
        )[1] as doi,
        list_filter(
            list_transform(creators, lambda c: {{ clean_text('c') }}),
            lambda c: c is not null
        ) as author_names,
        list_transform(subjects, lambda s: {{ clean_text('s') }}) as subjects,
        {{ clean_text('languages[1]') }} as language,
        {{ clean_text('publishers[1]') }} as publisher,
        set_specs,
        is_deleted,
        try_cast(rtrim(datestamp_text, 'Z') as timestamp) as datestamp,
        fetched_at
    from fields

)

select
    dspace_item_id,
    handle,
    item_url,
    title,
    year,
    type,
    source_type,
    doi,
    author_names,
    len(author_names) as n_authors,
    {{ name_family('author_names[1]') }} as first_author_family_name,
    subjects,
    language,
    publisher,
    set_specs,
    is_deleted,
    datestamp,
    fetched_at
from standardised
