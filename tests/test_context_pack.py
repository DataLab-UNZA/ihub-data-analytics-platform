"""Tests for scripts/make_context_pack.py (the context pack for Claude chats)."""

import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "make_context_pack", ROOT / "scripts" / "make_context_pack.py"
)
pack_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pack_module)


def test_pack_has_every_section_and_fits() -> None:
    pack = pack_module.build()
    for heading in (
        "## How to use this pack",
        "## Project",
        "## Architecture",
        "## Conventions",
        "## Roadmap and status",
        "## Open issues",
        "## Deployment",
        "## Folder tree",
        "## Key Python interfaces",
        "## dbt models",
    ):
        assert heading in pack
    assert len(pack) <= pack_module.MAX_CHARS
    assert "class `Connector(ABC)`" in pack


def test_open_issues_skip_pull_requests(tmp_path: Path) -> None:
    issues = [
        {"number": 7, "title": "OpenAlex connector", "labels": [{"name": "connector"}]},
        {"number": 8, "title": "A pull request", "labels": [], "pull_request": {}},
    ]
    path = tmp_path / "issues.json"
    path.write_text(json.dumps(issues))
    text = pack_module.open_issues(path)
    assert "#7 OpenAlex connector [connector]" in text
    assert "pull request" not in text


def test_zip_contains_pack_and_student_docs(tmp_path: Path, monkeypatch) -> None:
    out, zipped = tmp_path / "context-pack.md", tmp_path / "pack.zip"
    monkeypatch.setattr("sys.argv", ["make_context_pack", "--out", str(out), "--zip", str(zipped)])
    pack_module.main()
    names = zipfile.ZipFile(zipped).namelist()
    assert "ihub-context-pack/context-pack.md" in names
    assert "ihub-context-pack/STUDENT_GUIDE.md" in names
