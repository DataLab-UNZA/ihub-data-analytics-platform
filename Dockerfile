# Container image for the iHub web app, deployed to Google Cloud Run.
# Built by .github/workflows/deploy.yml with the newest data release
# (data/ihub.duckdb) copied in. See docs/DEPLOYMENT.md and ADR-002.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (cached between builds), without dev or pipeline tools.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY .streamlit ./.streamlit
RUN uv sync --frozen --no-dev

# The DuckDB file, when the deploy workflow has downloaded one (read-only).
COPY data ./data

RUN useradd --create-home --uid 10001 app
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    IHUB_DUCKDB_PATH=/app/data/ihub.duckdb \
    PORT=8080

EXPOSE 8080
CMD ["sh", "-c", "exec streamlit run src/ihub/app/Home.py --server.port=${PORT} --server.address=0.0.0.0"]
