"""Saved charts and dashboards, in the style of Apache Superset.

- ``models``       Chart, Dashboard, a dashboard's layout and its native filters
- ``store``        the repository interface; ``sqlite_store`` implements it
- ``service``      the rules: who may see, create, change and delete what
- ``api``          the FastAPI routes under /api/charts and /api/dashboards

Viewing needs ``research:read``; creating needs ``reports:manage``; only the owner or an
administrator (``users:manage``) may change or delete. Draft dashboards are visible to their
owner and administrators only; published ones to everyone who can read research.
"""
