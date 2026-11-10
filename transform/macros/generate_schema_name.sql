{#- Use the schema configured on a model exactly (staging, intermediate, marts) instead of
    dbt's default "<target schema>_<custom schema>" (for example main_marts). The app and
    the docs refer to these schemas by name. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
