"""Streamlit entry point.

Run locally with:  uv run streamlit run src/ihub/app/Home.py

This file only starts the shared shell in ``ihub.app.layout``. Pages live in
``src/ihub/app/pages/`` and are listed in ``layout.PAGES``. Pages must not contain SQL: they
call query functions in ``ihub.mart``, so the UI can be replaced later without touching the
data layer.
"""

from ihub.app import layout

layout.run()
