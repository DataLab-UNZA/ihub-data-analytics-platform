"""Read-only JSON API over the research mart, used by the Next.js front end (``web/``).

It holds no SQL: every route calls a function in :mod:`ihub.mart`, exactly as the Streamlit
pages do. Run it with ``uv run uvicorn ihub.api.app:app --port 8000``.
"""
