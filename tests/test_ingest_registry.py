"""The ingest registry and config/sources.yml must describe the same connectors."""

from pathlib import Path

from ihub.ingest.__main__ import CONFIG_PATH, CONNECTORS, load_source_config

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_every_registered_connector_has_a_block_in_sources_yml() -> None:
    sources = load_source_config(REPO_ROOT / CONFIG_PATH)
    for connector_cls in CONNECTORS:
        assert connector_cls.source_name in sources, connector_cls.__name__


def test_source_names_are_unique() -> None:
    names = [connector_cls.source_name for connector_cls in CONNECTORS]
    assert len(names) == len(set(names))


def test_an_enabled_repository_has_an_endpoint() -> None:
    """A source without a confirmed endpoint must not run in the weekly pipeline."""
    dspace = load_source_config(REPO_ROOT / CONFIG_PATH)["dspace_oai"]
    assert dspace["enabled"] is False or dspace["oai_endpoint"]


def test_ojs_lists_fifteen_distinct_journals() -> None:
    ojs = load_source_config(REPO_ROOT / CONFIG_PATH)["ojs"]
    assert ojs["base_url"]
    assert len(ojs["journals"]) == len({j.lower() for j in ojs["journals"]}) == 15


def test_configured_ca_certificate_files_exist() -> None:
    for name, source in load_source_config(REPO_ROOT / CONFIG_PATH).items():
        for path in source.get("ca_certificates") or []:
            assert (REPO_ROOT / path).is_file(), f"{name}: {path}"
