"""IHUB_ALLOWED_EMAIL_DOMAIN=* accepts any address.

Every other check still applies: verified email, signature, audience, issuer, nonce,
expiry and the code rules.
"""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from ihub.auth.config import AuthConfig
from ihub.auth.errors import IdentityRejectedError, InvalidEmailError
from ihub.auth.factory import build_auth_service
from ihub.auth.rbac import Role
from ihub.settings import Settings
from tests.auth_helpers import DROP, SECRET, Harness, make_harness

GMAIL = "someone.testing@gmail.com"


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path, domain="*", bootstrap_admins=frozenset({GMAIL}))


def test_any_well_formed_address_is_accepted() -> None:
    config = AuthConfig(secret=SECRET, allowed_domain="*")
    assert config.allows_any_domain
    assert config.normalise_email(" Someone@Gmail.com ") == "someone@gmail.com"
    assert config.normalise_email("staff@unza.ac.zm") == "staff@unza.ac.zm"
    for malformed in ("no-at-sign", "@gmail.com", "a b@gmail.com"):
        with pytest.raises(InvalidEmailError):
            config.normalise_email(malformed)


def test_gmail_accounts_sign_in_with_google(h: Harness) -> None:
    h.google.claims = {"hd": DROP, "email": GMAIL}
    result = h.sign_in_with_google()
    assert result.user.email == GMAIL
    assert result.user.role is Role.ADMIN  # bootstrap admins work for any address


def test_other_workspace_accounts_sign_in_with_google(h: Harness) -> None:
    h.google.claims = {"hd": "example.org", "email": "staff@example.org"}
    assert h.sign_in_with_google().user.email == "staff@example.org"


def test_google_is_not_limited_to_one_workspace(h: Harness) -> None:
    query = parse_qs(urlparse(h.service.start_google().authorization_url).query)
    assert "hd" not in query


def test_the_other_google_checks_still_apply(h: Harness) -> None:
    h.google.claims = {"hd": DROP, "email": GMAIL, "email_verified": False}
    with pytest.raises(IdentityRejectedError):
        h.sign_in_with_google()
    h.google.claims = {"hd": DROP, "email": GMAIL, "aud": "someone-elses-client"}
    with pytest.raises(IdentityRejectedError):
        h.sign_in_with_google()


def test_email_codes_go_to_any_address(h: Harness) -> None:
    assert h.sign_in_by_email(GMAIL).user.email == GMAIL


def test_any_domain_is_allowed_in_production_with_the_explicit_ephemeral_store(
    tmp_path: Path,
) -> None:
    base = {
        "_env_file": None,
        "ihub_auth_db_path": tmp_path / "auth.sqlite",
        "ihub_allowed_email_domain": "*",
        "ihub_auth_secret": "a-local-development-secret-of-48-characters-long",
    }
    service = build_auth_service(Settings(**base, ihub_allow_ephemeral_auth=True))
    assert service.allowed_domain == "*"
    service = build_auth_service(Settings(**base, ihub_env="development"))
    assert service.allowed_domain == "*"
