"""Building the auth service from settings: safe defaults and clear refusals (ADR-010)."""

from pathlib import Path

import pytest

from ihub.auth.errors import AuthNotConfiguredError
from ihub.auth.factory import build_auth_service
from ihub.settings import Settings

SECRET = "a-local-development-secret-of-48-characters-long"


def settings(tmp_path: Path, **values: object) -> Settings:
    return Settings(_env_file=None, ihub_auth_db_path=tmp_path / "auth.sqlite", **values)


def test_production_is_the_default_and_needs_a_secret(tmp_path: Path) -> None:
    with pytest.raises(AuthNotConfiguredError, match="IHUB_AUTH_SECRET is not set"):
        build_auth_service(settings(tmp_path))


def test_production_refuses_a_temporary_user_store(tmp_path: Path) -> None:
    with pytest.raises(AuthNotConfiguredError, match="persistent user store"):
        build_auth_service(settings(tmp_path, ihub_auth_secret=SECRET))


def test_short_secrets_are_refused(tmp_path: Path) -> None:
    with pytest.raises(AuthNotConfiguredError, match="at least 32"):
        build_auth_service(settings(tmp_path, ihub_env="development", ihub_auth_secret="short"))


def test_development_runs_with_a_temporary_secret_and_console_codes(tmp_path: Path) -> None:
    service = build_auth_service(settings(tmp_path, ihub_env="development"))
    assert service.methods == {"google": False, "email_code": True}
    assert service.allowed_domain == "unza.ac.zm"


def test_google_is_offered_only_when_fully_configured(tmp_path: Path) -> None:
    partial = settings(tmp_path, ihub_env="development", ihub_google_client_id="id")
    assert build_auth_service(partial).methods["google"] is False
    full = settings(
        tmp_path,
        ihub_env="development",
        ihub_google_client_id="id",
        ihub_google_client_secret="secret",
        ihub_public_url="http://localhost:3000",
    )
    assert build_auth_service(full).methods["google"] is True
