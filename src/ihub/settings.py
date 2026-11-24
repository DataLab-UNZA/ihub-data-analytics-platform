"""Runtime settings, read from environment variables (or a local .env file).

Never hard-code secrets. Every name used here must also appear in .env.example.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # Storage
    ihub_data_dir: Path = Path("data")
    ihub_duckdb_path: Path = Path("data/ihub.duckdb")
    # Private HR roster used to credit schools (ADR-012). Git-ignored; absent in production.
    ihub_staff_roster_path: Path = Path("data/private/staff_roster.csv")
    # Published CSV of the public staff list (names, title, occupation, school; ADR-017)
    unza_staff_list_url: str | None = None

    # OpenAlex
    openalex_mailto: str | None = None
    openalex_api_key: str | None = None

    # ORCID public API (client credentials)
    orcid_client_id: str | None = None
    orcid_client_secret: str | None = None

    # OJS REST API (optional; OAI-PMH needs no token)
    ojs_api_token: str | None = None

    # Environment: "production" (the safe default) or "development" (local conveniences).
    ihub_env: str = "production"

    # Authentication and access control (ADR-010)
    ihub_require_sign_in: bool = True
    ihub_auth_secret: SecretStr | None = None
    ihub_public_url: str | None = None
    ihub_allowed_email_domain: str = "unza.ac.zm"
    ihub_bootstrap_admins: str = ""
    ihub_auth_db_path: Path = Path("data/auth.sqlite")
    # Explicitly allow the non-durable SQLite store in a production container.
    # It is for demonstrations only: Cloud Run can erase it at any restart.
    ihub_allow_ephemeral_auth: bool = False
    # Saved charts and dashboards (ihub.workspace)
    ihub_workspace_db_path: Path = Path("data/workspace.sqlite")
    ihub_google_client_id: str | None = None
    ihub_google_client_secret: SecretStr | None = None
    # Outgoing mail (ihub.mail): smtp, console, or a registered transport
    ihub_mail_transport: str | None = None
    ihub_smtp_host: str | None = None
    ihub_smtp_port: int = 587
    ihub_smtp_username: str | None = None
    ihub_smtp_password: SecretStr | None = None
    ihub_smtp_from: str | None = None
    ihub_smtp_ssl: bool = False


def get_settings() -> Settings:
    return Settings()
