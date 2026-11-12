"""The dbt profile must find the same DuckDB file as the Python code, whatever the path form.

dbt runs from ``transform/``, but ``IHUB_DUCKDB_PATH`` in ``.env`` is relative to the
repository root, so a relative path has to be taken from the root (one level up).
"""

import os
from argparse import Namespace
from pathlib import Path

import pytest
from dbt.config.profile import Profile, read_profile
from dbt.config.renderer import ProfileRenderer
from dbt.flags import set_from_args
from dbt_common.context import set_invocation_context

TRANSFORM = Path(__file__).resolve().parent.parent / "transform"


def rendered_path() -> str:
    """Render ``transform/profiles.yml`` as dbt does and return the DuckDB path."""
    set_from_args(Namespace(), None)
    set_invocation_context(os.environ)
    profile = Profile.from_raw_profiles(read_profile(str(TRANSFORM)), "ihub", ProfileRenderer({}))
    return profile.credentials.path


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("data/ihub.duckdb", "../data/ihub.duckdb"),  # .env.example: from the repository root
        ("data/try.duckdb", "../data/try.duckdb"),
        ("/srv/ihub/data/ihub.duckdb", "/srv/ihub/data/ihub.duckdb"),  # CI, Docker
        ("C:/Users/me/ihub.duckdb", "C:/Users/me/ihub.duckdb"),  # Windows
        ("C:\\Users\\me\\ihub.duckdb", "C:\\Users\\me\\ihub.duckdb"),
        ("", "../data/ihub.duckdb"),  # set but empty: the default
    ],
)
def test_the_duckdb_path_is_taken_from_the_repository_root(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: str
) -> None:
    monkeypatch.setenv("IHUB_DUCKDB_PATH", value)
    assert rendered_path() == expected


def test_without_the_variable_the_default_file_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IHUB_DUCKDB_PATH", raising=False)
    assert rendered_path() == "../data/ihub.duckdb"
