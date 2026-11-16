"""Access tokens, refresh-token rotation and theft detection, and OAuth flow state."""

from pathlib import Path

import jwt
import pytest

from ihub.auth.errors import InvalidRequestError, InvalidTokenError
from ihub.auth.rbac import Role
from ihub.auth.tokens import ACCESS_AUDIENCE, ISSUER, RefreshTokenReuseError
from tests.auth_helpers import SECRET, STAFF, Harness, make_harness


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


def test_access_token_identifies_the_user_and_role(h: Harness) -> None:
    result = h.sign_in_by_email()
    principal = h.service.principal(result.access_token)
    assert principal.user_id == result.user.user_id
    assert principal.email == STAFF
    assert principal.role is Role.MEMBER
    assert result.access_expires_in == 15 * 60


def test_access_token_expires_after_15_minutes(h: Harness) -> None:
    token = h.sign_in_by_email().access_token
    h.clock.advance(minutes=14)
    h.service.principal(token)
    h.clock.advance(minutes=1)
    with pytest.raises(InvalidTokenError):
        h.service.principal(token)


def test_forged_and_tampered_access_tokens_are_refused(h: Harness) -> None:
    good = h.sign_in_by_email().access_token
    claims = jwt.decode(good, options={"verify_signature": False})
    forged_admin = jwt.encode({**claims, "role": "admin"}, SECRET, algorithm="HS256")
    unsigned = jwt.encode(claims, None, algorithm="none")
    flipped = good[:-4] + ("BBBB" if good.endswith("AAAA") else "AAAA")
    for token in (forged_admin, unsigned, flipped, "not-a-jwt", ""):
        with pytest.raises(InvalidTokenError):
            h.service.principal(token)
    assert claims["iss"] == ISSUER and claims["aud"] == ACCESS_AUDIENCE


def test_a_refresh_token_is_not_an_access_token(h: Harness) -> None:
    result = h.sign_in_by_email()
    with pytest.raises(InvalidTokenError):
        h.service.principal(result.refresh_token)


def test_refresh_rotates_the_token(h: Harness) -> None:
    first = h.sign_in_by_email()
    second = h.service.refresh(first.refresh_token)
    assert second.refresh_token != first.refresh_token
    assert h.service.principal(second.access_token).user_id == first.user.user_id
    third = h.service.refresh(second.refresh_token)
    assert third.user == second.user


def test_parallel_refreshes_within_the_grace_period_are_allowed(h: Harness) -> None:
    first = h.sign_in_by_email()
    winner = h.service.refresh(first.refresh_token)
    h.clock.advance(seconds=10)
    loser = h.service.refresh(first.refresh_token)  # a racing request with the old token
    for result in (winner, loser):
        h.service.refresh(result.refresh_token)


def test_reusing_a_rotated_token_later_revokes_the_whole_session(h: Harness) -> None:
    stolen = h.sign_in_by_email().refresh_token
    legitimate = h.service.refresh(stolen)
    h.clock.advance(seconds=21)
    with pytest.raises(RefreshTokenReuseError):
        h.service.refresh(stolen)
    with pytest.raises(InvalidTokenError):
        h.service.refresh(legitimate.refresh_token)  # the family is gone too
    assert h.store.audit.recent(1)[0].kind == "refresh_token_reuse"


def test_refresh_tokens_expire_after_7_days_without_use(h: Harness) -> None:
    result = h.sign_in_by_email()
    assert result.refresh_expires_in == 7 * 24 * 3600
    h.clock.advance(days=7)
    with pytest.raises(InvalidTokenError):
        h.service.refresh(result.refresh_token)


def test_a_session_ends_after_30_days_even_when_refreshed(h: Harness) -> None:
    token = h.sign_in_by_email().refresh_token
    for _ in range(4):
        h.clock.advance(days=6)
        token = h.service.refresh(token).refresh_token
    h.clock.advance(days=6)  # day 30
    with pytest.raises(InvalidTokenError):
        h.service.refresh(token)


def test_sign_out_ends_the_session(h: Harness) -> None:
    result = h.sign_in_by_email()
    rotated = h.service.refresh(result.refresh_token)
    h.service.sign_out(rotated.refresh_token)
    with pytest.raises(InvalidTokenError):
        h.service.refresh(rotated.refresh_token)
    h.service.sign_out("unknown-token")  # signing out twice, or with junk, is harmless


def test_refresh_tokens_are_stored_only_as_hashes(h: Harness) -> None:
    result = h.sign_in_by_email()
    assert result.refresh_token.encode() not in h.db_path.read_bytes()


def test_flow_state_cannot_be_tampered_with_or_reused_late(h: Harness) -> None:
    start = h.service.start_google("/topics")
    state = h.google.browser_visits(start.authorization_url)
    tampered = start.flow[:-4] + ("BBBB" if start.flow.endswith("AAAA") else "AAAA")
    with pytest.raises(InvalidRequestError):
        h.service.finish_google(code="good-code", state=state, flow=tampered)
    h.clock.advance(minutes=11)
    with pytest.raises(InvalidRequestError):
        h.service.finish_google(code="good-code", state=state, flow=start.flow)
