"""The FastAPI application: error handling, and the routes in :mod:`ihub.api.routes`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ihub.api.routes import build_router
from ihub.mart.research import MartUnavailableError
from ihub.settings import get_settings


def create_app(database_path: Callable[[], Path] | None = None) -> FastAPI:
    """Build the app. ``database_path`` returns the DuckDB file to read (settings by default)."""
    app = FastAPI(
        title="iHub research API",
        description="Read-only research metrics from the iHub research mart.",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.exception_handler(MartUnavailableError)
    async def mart_unavailable(_: Request, exc: MartUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(build_router(database_path or (lambda: get_settings().ihub_duckdb_path)))
    return app


app = create_app()
