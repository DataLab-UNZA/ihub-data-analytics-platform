"""The FastAPI application: error handling, the research routes in :mod:`ihub.api.routes`,
and the authentication and administration routes in :mod:`ihub.auth.api` (ADR-010)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ihub.api.routes import build_router
from ihub.auth.api import AuthServiceProvider, build_admin_router, build_auth_router
from ihub.auth.errors import AuthError
from ihub.auth.factory import build_auth_service
from ihub.auth.service import AuthService
from ihub.mart.research import MartUnavailableError
from ihub.settings import get_settings


class LazyAuthService:
    """Builds the auth service on first use and keeps it.

    A failure (for example a missing secret) is not cached, and only the auth routes see
    it, as a 503: the research routes keep working without authentication configured.
    """

    def __init__(self, build: Callable[[], AuthService]) -> None:
        self._build = build
        self._service: AuthService | None = None
        self._lock = threading.Lock()

    def __call__(self) -> AuthService:
        if self._service is None:
            with self._lock:
                if self._service is None:
                    self._service = self._build()
        return self._service


def create_app(
    database_path: Callable[[], Path] | None = None,
    auth_service: AuthServiceProvider | None = None,
) -> FastAPI:
    """Build the app.

    ``database_path`` returns the DuckDB file to read (settings by default);
    ``auth_service`` returns the authentication service (built from settings by default).
    """
    app = FastAPI(
        title="iHub research API",
        description="Research metrics from the iHub research mart, and sign-in (ADR-010).",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.auth_service = auth_service or LazyAuthService(
        lambda: build_auth_service(get_settings())
    )

    @app.exception_handler(MartUnavailableError)
    async def mart_unavailable(_: Request, exc: MartUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(AuthError)
    async def auth_error(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}, headers=exc.headers
        )

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(build_router(database_path or (lambda: get_settings().ihub_duckdb_path)))
    app.include_router(build_auth_router())
    app.include_router(build_admin_router())
    return app


app = create_app()
