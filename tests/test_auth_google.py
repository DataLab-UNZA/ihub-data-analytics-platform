"""Signing in with a UNZA Google account: OIDC code flow with PKCE (ADR-010).

Google is played by ``FakeGoogle``; no request leaves the test.
"""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from ihub.auth.errors import IdentityRejectedError, InvalidRequestError, MethodUnavailableError
from ihub.auth.google import AUTHORIZATION_ENDPOINT
from ihub.auth.rbac import Role
from tests.auth_helpers import (
    CLIENT_ID,
    DOMAIN,
    DROP,
    PUBLIC_URL,
    STAFF,
    Harness,
    make_harness,
    rsa_key,
)


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


def test_the_authorisation_url_asks_for_a_unza_account_with_pkce(h: Harness) -> None:
    url = h.service.start_google().authorization_url
    assert url.startswith(f"{AUTHORIZATION_ENDPOINT}?")
    query = {name: values[0] for name, values in parse_qs(urlparse(url).query).items()}
    assert query["client_id"] == CLIENT_ID
    assert query["redirect_uri"] == f"{PUBLIC_URL}/auth/google/callback"
    assert query["response_type"] == "code"
    assert query["scope"] == "openid email profile"
    assert query["code_challenge_method"] == "S256"
    assert query["hd"] == DOMAIN
    assert len(query["state"]) >= 32 and len(query["nonce"]) >= 32
    assert query["state"] != query["nonce"]


def test_google_sign_in_registers_the_user_and_returns_to_the_page(h: Harness) -> None:
    result = h.sign_in_with_google("/publications?q=malaria")
    assert result.user.email == STAFF
    assert result.user.name == "Test Staff"
    assert result.user.role is Role.MEMBER
    assert result.next_path == "/publications?q=malaria"
    request = h.google.token_requests[-1]
    assert request["grant_type"] == ["authorization_code"]
    assert request["redirect_uri"] == [f"{PUBLIC_URL}/auth/google/callback"]


def test_an_unsafe_return_address_becomes_the_overview(h: Harness) -> None:
    assert h.sign_in_with_google("https://evil.example/").next_path == "/overview"


@pytest.mark.parametrize(
    ("claims", "reason"),
    [
        ({"hd": DROP, "email": "someone@gmail.com"}, "wrong_domain"),  # a personal account
        # A consumer Google account created with a UNZA address: verified, but not managed
        # by UNZA's Workspace, so there is no hd claim. Only the hd check stops it.
        ({"hd": DROP}, "wrong_domain"),
        ({"hd": "other.ac.zm", "email": "someone@other.ac.zm"}, "wrong_domain"),
        ({"email": "someone@gmail.com"}, "wrong_domain"),  # hd right, address not
        ({"email_verified": False}, "unverified_email"),
        ({"aud": "someone-elses-client"}, "invalid_token"),
        ({"iss": "https://evil.example"}, "wrong_issuer"),
        ({"nonce": "replayed-nonce"}, "nonce_mismatch"),
        ({"exp": 1_000_000_000, "iat": 999_999_000}, "invalid_token"),
    ],
)
def test_tokens_failing_any_check_are_refused(
    h: Harness, claims: dict[str, object], reason: str
) -> None:
    h.google.claims = claims
    with pytest.raises(IdentityRejectedError) as caught:
        h.sign_in_with_google()
    assert caught.value.reason == reason
    assert h.store.users.list_all() == []
    event = h.store.audit.recent(1)[0]
    assert (event.kind, event.detail, event.user_id) == (
        "sign_in_refused",
        f"google:{reason}",
        None,
    )


def test_a_token_signed_by_another_key_is_refused(h: Harness) -> None:
    h.google.nonce = "expected-nonce"
    forged = h.google.id_token(key=rsa_key(1))
    with pytest.raises(IdentityRejectedError) as caught:
        h.google.client().verify_id_token(forged, nonce="expected-nonce")
    assert caught.value.reason == "invalid_token"


def test_the_state_must_match(h: Harness) -> None:
    start = h.service.start_google()
    h.google.browser_visits(start.authorization_url)
    with pytest.raises(InvalidRequestError, match="does not match"):
        h.service.finish_google(code="good-code", state="forged-state", flow=start.flow)


def test_a_code_google_rejects_fails_cleanly(h: Harness) -> None:
    start = h.service.start_google()
    state = h.google.browser_visits(start.authorization_url)
    with pytest.raises(InvalidRequestError, match="did not accept"):
        h.service.finish_google(code="stolen-code", state=state, flow=start.flow)


def test_a_flow_from_another_sign_in_fails_pkce(h: Harness) -> None:
    first = h.service.start_google()
    second = h.service.start_google()
    state = h.google.browser_visits(second.authorization_url)  # Google saw the second challenge
    first_state = parse_qs(urlparse(first.authorization_url).query)["state"][0]
    with pytest.raises(InvalidRequestError):
        h.service.finish_google(code="good-code", state=first_state, flow=first.flow)
    h.service.finish_google(code="good-code", state=state, flow=second.flow)


def test_without_a_client_google_is_unavailable(tmp_path: Path) -> None:
    h = make_harness(tmp_path, with_google=False)
    assert h.service.methods == {"google": False, "email_code": True}
    with pytest.raises(MethodUnavailableError):
        h.service.start_google()
