{#- Reading raw JSON payloads. Raw tables keep each record as fetched, in a JSON `payload`
    column; these helpers turn the parts staging needs into typed DuckDB values. -#}


{#- The JSON array at `path` as a list of text values; an empty list when it is missing.
    OAI-PMH metadata (Sickle) stores every Dublin Core element as such an array. -#}
{% macro json_text_list(json_expr, path) -%}
    coalesce(from_json({{ json_expr }} -> '{{ path }}', '["varchar"]'), []::varchar[])
{%- endmacro %}


{#- The JSON array at `path` as a list of JSON values, ready to unnest; an empty list when
    it is missing. -#}
{% macro json_list(json_expr, path) -%}
    coalesce(from_json({{ json_expr }} -> '{{ path }}', '["json"]'), []::json[])
{%- endmacro %}
