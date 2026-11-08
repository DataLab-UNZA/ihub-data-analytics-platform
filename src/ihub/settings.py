"""Runtime settings, read from environment variables (or a local .env file).

Never hard-code secrets. Every name used here must also appear in .env.example.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # Storage
    ihub_data_dir: Path = Path("data")
    ihub_duckdb_path: Path = Path("data/ihub.duckdb")

    # OpenAlex
    openalex_mailto: str | None = None
    openalex_api_key: str | None = None

    # ORCID public API (client credentials)
    orcid_client_id: str | None = None
    orcid_client_secret: str | None = None

    # OJS REST API (optional; OAI-PMH needs no token)
    ojs_api_token: str | None = None


def get_settings() -> Settings:
    return Settings()
