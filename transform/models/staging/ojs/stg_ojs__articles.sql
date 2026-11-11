-- One row per article in the UNZA journals on OJS: renamed, typed and standardised.
-- No joins across sources.
--
-- The connector stores two shapes, told apart by harvest_method:
--   oai_pmh   Dublin Core lists (every journal on journals.unza.zm today)
--   rest_api  the OJS REST API's issue and article objects (the fallback for a journal
--             without OAI-PMH)
-- Each shape has its own CTE that maps it onto the same columns (an adapter per shape);
-- `unioned` then treats every article alike. To support another shape, add one CTE.
--
-- OAI-PMH rules: the citation is the dc:source value that holds "Journal; Vol x No y
-- (year): ...; pages"; the journal name, volume, issue and pages are read from it. The DOI
-- is the first dc:identifier holding one (dc:relation and dc:source also hold galley and
-- issue DOIs, which are not the article's).

with latest as (

    {{ latest_delivery(source('raw_ojs', 'records')) }}

),

oai_fields as (

    select
        record_id,
        payload ->> '$.journal' as journal_path,
        payload ->> '$.datestamp' as datestamp_text,
        coalesce(try_cast(payload ->> '$.deleted' as boolean), false) as is_deleted,
        {{ json_text_list('payload', '$.metadata.title') }} as titles,
        {{ json_text_list('payload', '$.metadata.creator') }} as creators,
        {{ json_text_list('payload', '$.metadata.date') }} as dates,
        {{ json_text_list('payload', '$.metadata.type') }} as types,
        {{ json_text_list('payload', '$.metadata.identifier') }} as identifiers,
        {{ json_text_list('payload', '$.metadata.source') }} as sources,
        {{ json_text_list('payload', '$.metadata.language') }} as languages,
        fetched_at
    from latest
    where payload ->> '$.harvest_method' = 'oai_pmh'

),

oai_articles as (

    select
        record_id,
        journal_path,
        'oai_pmh' as harvest_method,
        {{ clean_text('titles[1]') }} as title,
        try_cast(dates[1] as date) as published_date,
        {{ year_from_text('dates[1]') }} as year,
        list_filter(types, lambda t: t not ilike '%version')[1] as source_type,
        list_filter(
            list_transform(identifiers, lambda i: {{ normalise_doi('i') }}),
            lambda d: d is not null
        )[1] as doi,
        list_filter(identifiers, lambda i: i like '%/article/view/%')[1] as article_url,
        list_filter(sources, lambda s: contains(s, ';'))[1] as citation,
        list_filter(
            sources, lambda s: regexp_full_match(trim(s), '[0-9]{4}-[0-9]{3}[0-9Xx]')
        ) as issns,
        list_filter(
            list_transform(creators, lambda c: {{ clean_text('c') }}),
            lambda c: c is not null
        ) as author_names,
        {{ clean_text('languages[1]') }} as language,
        is_deleted,
        try_cast(rtrim(datestamp_text, 'Z') as timestamp) as datestamp,
        fetched_at
    from oai_fields

),

oai_standardised as (

    select
        record_id,
        journal_path,
        harvest_method,
        title,
        published_date,
        year,
        source_type,
        doi,
        article_url,
        -- The journal name, without the ISSNs and acronyms some journals add to it, e.g.
        -- "Zambia Law Journal (ZLJ) ISSN Print: 1027-7862" becomes "Zambia Law Journal".
        -- Everything from the first "(" or "ISSN" on is dropped.
        {{ clean_text(
            "regexp_replace(split_part(citation, ';', 1),"
            ~ " '\\s*(\\(|-\\s*ISSN|Online-ISSN|ISSN).*$', '', 'i')"
        ) }} as venue_name,
        issns,
        nullif(regexp_extract(citation, 'Vol\.?\s*([0-9A-Za-z]+)', 1), '') as volume,
        nullif(regexp_extract(citation, 'No\.?\s*([0-9A-Za-z]+)', 1), '') as issue,
        nullif(
            replace(regexp_extract(citation, ';\s*([0-9]+\s*-\s*[0-9]+)\s*$', 1), ' ', ''),
            ''
        ) as pages,
        author_names,
        language,
        is_deleted,
        datestamp,
        fetched_at
    from oai_articles

),

rest_fields as (

    select
        record_id,
        payload ->> '$.journal' as journal_path,
        payload -> '$.issue' as issue_json,
        payload -> '$.article' as article_json,
        -- the newest version of the article is the last publication
        payload -> '$.article.publications[#-1]' as publication_json,
        fetched_at
    from latest
    where payload ->> '$.harvest_method' = 'rest_api'

),

rest_articles as (

    select
        record_id,
        journal_path,
        'rest_api' as harvest_method,
        {{ clean_text(
            "coalesce(publication_json ->> '$.title.en_US', publication_json ->> '$.title.en',"
            ~ " json_extract_string(publication_json, '$.title.*')[1])"
        ) }} as title,
        try_cast(
            left(coalesce(publication_json ->> '$.datePublished', issue_json ->> '$.datePublished'), 10)
            as date
        ) as published_date,
        coalesce(
            {{ year_from_text("publication_json ->> '$.datePublished'") }},
            try_cast(issue_json ->> '$.year' as integer)
        ) as year,
        'article' as source_type,
        {{ normalise_doi("publication_json ->> '$.doiObject.doi'") }} as doi,
        article_json ->> '$.urlPublished' as article_url,
        cast(null as varchar) as venue_name,
        []::varchar[] as issns,
        issue_json ->> '$.volume' as volume,
        issue_json ->> '$.number' as issue,
        nullif(replace(publication_json ->> '$.pages', ' ', ''), '') as pages,
        list_filter(
            list_transform(
                string_split(coalesce(publication_json ->> '$.authorsString', ''), ';'),
                lambda a: {{ clean_text('a') }}
            ),
            lambda a: a is not null
        ) as author_names,
        cast(null as varchar) as language,
        false as is_deleted,
        cast(null as timestamp) as datestamp,
        fetched_at
    from rest_fields

),

unioned as (

    select * from oai_standardised
    union all by name
    select * from rest_articles

)

select
    record_id as ojs_article_id,
    journal_path,
    harvest_method,
    try_cast(regexp_extract(record_id, 'article/([0-9]+)$', 1) as integer) as article_number,
    title,
    published_date,
    year,
    {{ standardise_publication_type('source_type') }} as type,
    source_type,
    doi,
    article_url,
    venue_name,
    issns,
    volume,
    issue,
    pages,
    author_names,
    len(author_names) as n_authors,
    {{ name_family('author_names[1]') }} as first_author_family_name,
    language,
    is_deleted,
    datestamp,
    fetched_at
from unioned
