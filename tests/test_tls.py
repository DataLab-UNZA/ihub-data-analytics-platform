"""Tests for the extra-CA support used by sources with an incomplete certificate chain."""

import ssl
from pathlib import Path

import certifi
import pytest

from ihub.connectors.oai_pmh import OaiPmhHarvester
from ihub.connectors.tls import ca_bundle, ssl_context

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTIGO_R36 = REPO_ROOT / "config/certs/sectigo-public-server-authentication-ca-dv-r36.crt"


def test_no_extra_certificates_means_the_standard_bundle() -> None:
    assert ca_bundle(None) is True
    assert ca_bundle([]) is True


def test_the_bundle_holds_the_standard_bundle_and_the_extra_certificate() -> None:
    bundle = Path(ca_bundle([SECTIGO_R36]))
    text = bundle.read_text(encoding="ascii")
    assert text.startswith(Path(certifi.where()).read_text(encoding="ascii"))
    assert "Sectigo Public Server Authentication CA DV R36" in text
    assert ca_bundle([SECTIGO_R36]) == str(bundle)  # reused, not rewritten


def test_the_ssl_context_checks_certificates_and_trusts_the_extra_one() -> None:
    default_count = len(ssl_context(None).get_ca_certs())
    context = ssl_context([SECTIGO_R36])
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert len(context.get_ca_certs()) == default_count + 1


def test_a_missing_or_wrong_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        ca_bundle([tmp_path / "missing.pem"])
    not_a_cert = tmp_path / "notes.pem"
    not_a_cert.write_text("hello", encoding="ascii")
    with pytest.raises(ValueError, match="does not hold a PEM certificate"):
        ssl_context([not_a_cert])


def test_the_harvester_never_turns_checking_off() -> None:
    with pytest.raises(ValueError, match="cannot be turned off"):
        OaiPmhHarvester("https://journals.unza.zm/index.php/zjh/oai", verify=False)


def test_the_harvester_uses_the_configured_certificates() -> None:
    harvester = OaiPmhHarvester.from_config(
        "https://journals.unza.zm/index.php/zjh/oai", {"ca_certificates": [str(SECTIGO_R36)]}
    )
    assert harvester._sickle.request_args["verify"] == ca_bundle([SECTIGO_R36])
