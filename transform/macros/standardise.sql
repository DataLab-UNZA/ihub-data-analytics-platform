{#- Shared standardisation rules for the staging models.

    Every source cleans DOIs, titles, names, years and publication types with these macros,
    so a value means the same thing whichever source it came from and cross-source matching
    (int_publications__source_records) compares like with like. Each macro returns one SQL
    expression and takes the SQL expression to clean, so it works on columns and inside
    list lambdas alike. Change a rule here and every source follows. -#}


{#- A DOI in lower case with any https://doi.org/, dx.doi.org or "doi:" prefix removed,
    or null when the text holds no DOI. Trailing sentence punctuation is dropped. -#}
{% macro normalise_doi(expr) -%}
    nullif(
        rtrim(regexp_extract(lower(trim({{ expr }})), '(10\.[0-9]{4,9}/[^\s"<>]+)', 1), '.,;'),
        ''
    )
{%- endmacro %}


{#- A title for matching: lower case, accents removed, anything but letters and digits
    becomes one space. Null when nothing is left. -#}
{% macro normalise_title(expr) -%}
    nullif(trim(regexp_replace(strip_accents(lower({{ expr }})), '[^a-z0-9]+', ' ', 'g')), '')
{%- endmacro %}


{#- An organisation or department name for matching aliases: like normalise_title, but
    "&" (also written "&amp;") counts as "and" and a leading "the" is dropped. -#}
{% macro normalise_org_name(expr) -%}
    nullif(
        regexp_replace(
            {{ normalise_title("replace(replace(" ~ expr ~ ", '&amp;', ' and '), '&', ' and ')") }},
            '^the ',
            ''
        ),
        ''
    )
{%- endmacro %}


{#- The key a department name is matched on. The department_aliases seed is matched on it,
    so every source's names must be reduced with this same macro.

    Starting from normalise_org_name, it keeps the department itself:
      - what follows the last "department of" (also "dept", "division", "section", "unit"),
        so "School of Engineering, Department of Geomatic Engineering" becomes
        "geomatic engineering";
      - without a trailing "department" or "dept": "Pharmacy Department" becomes "pharmacy";
      - without a trailing "school of ...": "Paraclinical Studies, School of Veterinary
        Medicine" becomes "paraclinical studies".
    A name that starts with "school of" keeps it, because "School of Medicine" and
    "Department of Medicine" are different units. The school named in a compound name is
    dropped here; matching uses it separately, as the alias's school context. -#}
{% macro department_name_key(expr) -%}
    nullif(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    {{ normalise_org_name(expr) }},
                    '^.*\b(department|dept|division|section|unit) (of|for) ',
                    ''
                ),
                ' (department|dept)$',
                ''
            ),
            '(.) school of .*$',
            '\1'
        ),
        ''
    )
{%- endmacro %}


{#- Text with runs of white space collapsed to one space and trimmed; null when empty. -#}
{% macro clean_text(expr) -%}
    nullif(trim(regexp_replace({{ expr }}, '\s+', ' ', 'g')), '')
{%- endmacro %}


{#- The first plausible publication year (1800 to 2099) found in a date or citation text. -#}
{% macro year_from_text(expr) -%}
    try_cast(regexp_extract({{ expr }}, '(18[0-9]{2}|19[0-9]{2}|20[0-9]{2})', 1) as integer)
{%- endmacro %}


{#- The family name from a personal name written "Family, Given" (the Dublin Core and OJS
    convention) or "Given Family". -#}
{% macro name_family(expr) -%}
    {{ clean_text(
        "case when contains(" ~ expr ~ ", ',') then split_part(" ~ expr ~ ", ',', 1)"
        ~ " else regexp_extract(trim(" ~ expr ~ "), '(\\S+)$', 1) end"
    ) }}
{%- endmacro %}


{#- The given names from a personal name written "Family, Given" or "Given Family". -#}
{% macro name_given(expr) -%}
    {{ clean_text(
        "case when contains(" ~ expr ~ ", ',')"
        ~ " then substr(" ~ expr ~ ", strpos(" ~ expr ~ ", ',') + 1)"
        ~ " else regexp_replace(trim(" ~ expr ~ "), '\\s*\\S+$', '') end"
    ) }}
{%- endmacro %}


{#- A source's own publication type mapped to the OpenAlex vocabulary used by the marts
    (article, review, book, book-chapter, dissertation, preprint, dataset, report,
    editorial, letter, other). Unrecognised types become "other". -#}
{% macro standardise_publication_type(expr) -%}
    case
        when {{ expr }} is null then null
        when regexp_matches(lower({{ expr }}), '(thesis|dissertation)') then 'dissertation'
        when regexp_matches(lower({{ expr }}), 'review') then 'review'
        when regexp_matches(lower({{ expr }}), '(book.?chapter|book.?part|book.?section|chapter)')
            then 'book-chapter'
        when regexp_matches(lower({{ expr }}), '(^|[^a-z])book($|[^a-z])') then 'book'
        when regexp_matches(lower({{ expr }}), 'editorial') then 'editorial'
        when regexp_matches(lower({{ expr }}), '(^|[^a-z])letter') then 'letter'
        when regexp_matches(lower({{ expr }}), '(preprint|working.?paper)') then 'preprint'
        when regexp_matches(lower({{ expr }}), '(data.?set|dataset)') then 'dataset'
        when regexp_matches(lower({{ expr }}), '(report|technical)') then 'report'
        when regexp_matches(
            lower({{ expr }}),
            '(abstract|poster|presentation|lecture|speech|newspaper|newsletter|magazine|blog)'
        ) then 'other'
        when regexp_matches(lower({{ expr }}), '(article|conference|paper|proceeding)')
            then 'article'
        else 'other'
    end
{%- endmacro %}
