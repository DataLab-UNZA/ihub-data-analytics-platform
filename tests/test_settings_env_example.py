"""CLAUDE.md: every setting the code reads must be listed in .env.example."""

from pathlib import Path

from ihub.settings import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def test_every_setting_is_listed_in_env_example() -> None:
    listed = {
        line.split("=", 1)[0].strip()
        for line in ENV_EXAMPLE.read_text().splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    missing = {name.upper() for name in Settings.model_fields} - listed
    assert not missing, f"Add to .env.example: {sorted(missing)}"
