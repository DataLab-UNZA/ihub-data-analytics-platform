-- One row per work on a UNZA researcher's ORCID record: renamed, typed and standardised.
-- No joins across sources.
--
-- ORCID groups the copies of one work that different sources (Crossref, the researcher,
-- ...) added to a record; this model keeps one row per group, described by its preferred
-- work summary: the one with the highest display-index (the first summary if none has
-- one). On the real data the preferred summary was always listed first, but the order is
-- not relied on. The DOI comes from the group's own identifiers (type doi, relationship
-- self), so a DOI for a work the record merely cites ("part-of", "version-of") is never
-- taken as this work's DOI.

with latest as (

    {{ latest_delivery(source('raw_orcid', 'records')) }}

),

-- Take the small columns and the list of groups first, then unnest in the next step. If
-- the payload were still selected next to unnest(), DuckDB would copy the whole payload
-- onto every unnested row: one real record of 8.4 MB lists thousands of works, which ran
-- out of memory.
group_lists as (

    select
        coalesce(payload ->> '$.orcid', record_id) as orcid_id,
        {{ json_list('payload', '$.works.group') }} as groups,
        fetched_at
    from latest

),

work_groups as (

    select orcid_id, unnest(groups) as work_group, fetched_at
    from group_lists

),

summary_lists as (

    select
        orcid_id,
        {{ json_list('work_group', '$."work-summary"') }} as summaries,
        {{ json_list('work_group', '$."external-ids"."external-id"') }} as external_ids,
        fetched_at
    from work_groups

),

preferred as (

    select
        orcid_id,
        coalesce(
            list_filter(
                summaries,
                lambda s: try_cast(s ->> '$."display-index"' as integer) = list_max(
                    list_transform(
                        summaries, lambda t: try_cast(t ->> '$."display-index"' as integer)
                    )
                )
            )[1],
            summaries[1]
        ) as summary,
        external_ids,
        fetched_at
    from summary_lists

),

fields as (

    select
        orcid_id,
        summary ->> '$."put-code"' as put_code,
        {{ clean_text("summary ->> '$.title.title.value'") }} as title,
        {{ clean_text("summary ->> '$.title.subtitle.value'") }} as subtitle,
        try_cast(summary ->> '$."publication-date".year.value' as integer) as year,
        summary ->> '$.type' as source_type,
        list_filter(
            list_transform(
                list_filter(
                    external_ids,
                    lambda e: e ->> '$."external-id-type"' = 'doi'
                        and coalesce(e ->> '$."external-id-relationship"', 'self') = 'self'
                ),
                lambda e: {{ normalise_doi("e ->> '$.\"external-id-value\"'") }}
            ),
            lambda d: d is not null
        )[1] as doi,
        {{ clean_text("summary ->> '$.\"journal-title\".value'") }} as journal_title,
        summary ->> '$.url.value' as work_url,
        summary ->> '$.source."source-name".value' as added_by,
        summary ->> '$.visibility' as visibility,
        fetched_at
    from preferred

)

select
    orcid_id || ':' || put_code as orcid_work_id,
    orcid_id,
    try_cast(put_code as bigint) as put_code,
    title,
    subtitle,
    year,
    {{ standardise_publication_type('source_type') }} as type,
    source_type,
    doi,
    journal_title,
    work_url,
    added_by,
    visibility,
    fetched_at
from fields
where put_code is not null
