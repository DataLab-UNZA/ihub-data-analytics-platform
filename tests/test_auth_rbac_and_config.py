"""The RBAC table, the UNZA email rule, key derivation and safe redirects (ADR-010)."""

import pytest

from ihub.auth.config import AuthConfig, parse_email_list
from ihub.auth.errors import InvalidEmailError
from ihub.auth.rbac import ROLE_PERMISSIONS, Permission, Role, permissions_for
from ihub.auth.service import DEFAULT_NEXT_PATH, safe_next_path
from tests.auth_helpers import SECRET


def test_every_role_has_permissions_and_can_read_research() -> None:
    assert set(ROLE_PERMISSIONS) == set(Role)
    for role in Role:
        assert Permission.RESEARCH_READ in permissions_for(role)


def test_admin_holds_every_permission() -> None:
    assert permissions_for(Role.ADMIN) == frozenset(Permission)


def test_only_admin_manages_users_and_sources() -> None:
    for role in Role:
        manages = {Permission.USERS_MANAGE, Permission.SOURCES_MANAGE} & permissions_for(role)
        assert bool(manages) is (role is Role.ADMIN)


def test_member_reads_but_cannot_export_or_review() -> None:
    assert permissions_for(Role.MEMBER) == frozenset({Permission.RESEARCH_READ})
    assert Permission.QUALITY_REVIEW in permissions_for(Role.LIBRARIAN)
    assert Permission.QUALITY_REVIEW not in permissions_for(Role.ANALYST)


@pytest.fixture
def config() -> AuthConfig:
    return AuthConfig(secret=SECRET, allowed_domain=" UNZA.ac.zm ")


def test_email_is_trimmed_and_lower_cased(config: AuthConfig) -> None:
    assert config.allowed_domain == "unza.ac.zm"
    assert config.normalise_email("  Test.Staff@UNZA.AC.ZM ") == "test.staff@unza.ac.zm"


@pytest.mark.parametrize(
    "address",
    [
        "someone@gmail.com",
        "someone@student.unza.ac.zm",  # subdomains are not the staff domain
        "someone@unza.ac.zm.evil.example",
        "someone@unza.zm",
        "@unza.ac.zm",
        "a@b@unza.ac.zm",
        "some one@unza.ac.zm",
        "no-at-sign",
        "",
    ],
)
def test_only_addresses_at_the_allowed_domain_pass(config: AuthConfig, address: str) -> None:
    with pytest.raises(InvalidEmailError):
        config.normalise_email(address)


def test_each_purpose_gets_its_own_key(config: AuthConfig) -> None:
    keys = {config.key(purpose) for purpose in ("access-token", "oauth-flow", "email-code")}
    assert len(keys) == 3
    assert all(len(key) == 32 and key != SECRET for key in keys)


def test_short_secrets_are_refused() -> None:
    with pytest.raises(ValueError, match="at least 32 bytes"):
        AuthConfig(secret=b"too-short")


def test_bootstrap_list_is_parsed() -> None:
    assert parse_email_list(" A@unza.ac.zm, ,b@UNZA.ac.zm ") == {"a@unza.ac.zm", "b@unza.ac.zm"}
    assert parse_email_list("") == frozenset()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/publications?q=malaria", "/publications?q=malaria"),
        ("/overview", "/overview"),
        (None, DEFAULT_NEXT_PATH),
        ("", DEFAULT_NEXT_PATH),
        ("https://evil.example/", DEFAULT_NEXT_PATH),
        ("//evil.example/", DEFAULT_NEXT_PATH),
        ("/\\evil.example", DEFAULT_NEXT_PATH),
        ("/overview\r\nSet-Cookie: x=1", DEFAULT_NEXT_PATH),
        ("javascript:alert(1)", DEFAULT_NEXT_PATH),
    ],
)
def test_return_paths_cannot_leave_the_site(value: str | None, expected: str) -> None:
    assert safe_next_path(value) == expected
