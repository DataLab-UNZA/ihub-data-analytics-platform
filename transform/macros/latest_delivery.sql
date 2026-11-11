{#- The newest delivery of every record in a raw table: one row per `key`.

    Raw tables keep every record exactly as fetched, so a record can arrive more than once
    (OpenAlex can return a work on two pages; DSpace returns an item once for every set
    harvested). Every staging model starts from this, so the rule is the same for all
    sources: the most recently fetched delivery wins, and ties are broken on a hash of the
    payload so the choice never changes between builds.

    The winners are chosen on small values only (key, fetch time, hash, rowid) and then
    read back by rowid, so large JSON payloads are never carried through the sort. On the
    real IRIMS and ORCID data, sorting whole payloads ran out of memory.

    `relation` must be a raw table (it uses DuckDB's rowid), e.g.
    source('raw_ojs', 'records'). `where` optionally keeps only some rows first (for a raw
    table holding several kinds of record, such as DSpace items and sets). -#}
{% macro latest_delivery(relation, key='record_id', where=none) -%}
    select *
    from {{ relation }}
    where rowid in (
        select rowid
        from {{ relation }}
        {% if where %}where {{ where }}{% endif %}
        qualify row_number() over (
            partition by {{ key }}
            order by fetched_at desc, md5(cast(payload as varchar))
        ) = 1
    )
{%- endmacro %}
