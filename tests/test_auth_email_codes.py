"""Signing in with a one-time code sent to a UNZA email address (ADR-010)."""

from pathlib import Path

import pytest

from ihub.auth.email_codes import sign_in_message
from ihub.auth.errors import (
    InvalidCodeError,
    InvalidEmailError,
    MethodUnavailableError,
    RateLimitedError,
)
from ihub.auth.rbac import Role
from tests.auth_helpers import ADMIN, STAFF, Harness, make_harness


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


def test_a_code_signs_in_and_registers_a_member(h: Harness) -> None:
    sent = h.service.request_email_code("Test.Staff@UNZA.ac.zm")
    assert (sent.expires_in, sent.resend_after) == (600, 30)
    address, code = h.email.sent[-1]
    assert address == STAFF and len(code) == 6 and code.isdigit()

    result = h.service.finish_email_code(email=STAFF, code=code)
    assert result.user.email == STAFF
    assert result.user.role is Role.MEMBER
    assert [event.kind for event in h.store.audit.recent()] == ["sign_in", "user_registered"]


def test_other_domains_get_no_code(h: Harness) -> None:
    with pytest.raises(InvalidEmailError, match="@unza.ac.zm"):
        h.service.request_email_code("someone@gmail.com")
    assert h.email.sent == []


def test_the_code_is_stored_as_a_keyed_hash(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    challenge = h.store.email_challenges.latest(STAFF)
    assert challenge is not None
    assert h.email.last_code not in challenge.code_hash
    assert len(challenge.code_hash) == 64


def test_wrong_codes_count_down_then_lock(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    right = h.email.last_code
    wrong = "000000" if right != "000000" else "111111"
    for left in (4, 3, 2, 1):
        with pytest.raises(InvalidCodeError, match=f"{left} attempt"):
            h.service.finish_email_code(email=STAFF, code=wrong)
    with pytest.raises(InvalidCodeError, match="Ask for a new code"):
        h.service.finish_email_code(email=STAFF, code=wrong)
    with pytest.raises(InvalidCodeError, match="Too many wrong attempts"):
        h.service.finish_email_code(email=STAFF, code=right)


def test_codes_expire_after_10_minutes(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    h.clock.advance(minutes=10)
    with pytest.raises(InvalidCodeError, match="expired"):
        h.service.finish_email_code(email=STAFF, code=h.email.last_code)


def test_a_code_works_once(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    code = h.email.last_code
    h.service.finish_email_code(email=STAFF, code=code)
    with pytest.raises(InvalidCodeError, match="already used"):
        h.service.finish_email_code(email=STAFF, code=code)


def test_spaces_in_a_typed_code_are_ignored(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    code = h.email.last_code
    h.service.finish_email_code(email=STAFF, code=f" {code[:3]} {code[3:]} ")


def test_a_new_code_replaces_the_old_one(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    old = h.email.last_code
    h.clock.advance(seconds=30)
    h.service.request_email_code(STAFF)
    if old != h.email.last_code:
        with pytest.raises(InvalidCodeError):
            h.service.finish_email_code(email=STAFF, code=old)
    h.service.finish_email_code(email=STAFF, code=h.email.last_code)


def test_one_code_every_30_seconds(h: Harness) -> None:
    h.service.request_email_code(STAFF)
    h.clock.advance(seconds=10)
    with pytest.raises(RateLimitedError) as caught:
        h.service.request_email_code(STAFF)
    assert caught.value.retry_after == 20
    assert caught.value.headers["Retry-After"] == "20"
    h.service.request_email_code(ADMIN)  # the limit is per address


def test_at_most_five_codes_an_hour(h: Harness) -> None:
    for _ in range(5):
        h.service.request_email_code(STAFF)
        h.clock.advance(seconds=31)
    with pytest.raises(RateLimitedError, match="Too many codes"):
        h.service.request_email_code(STAFF)
    h.clock.advance(minutes=60)
    h.service.request_email_code(STAFF)


def test_without_a_sender_the_method_is_unavailable(tmp_path: Path) -> None:
    h = make_harness(tmp_path, with_email=False)
    assert h.service.methods == {"google": True, "email_code": False}
    with pytest.raises(MethodUnavailableError):
        h.service.request_email_code(STAFF)


def test_the_email_says_how_long_the_code_lasts() -> None:
    message = sign_in_message(STAFF, "ihub-noreply@unza.ac.zm", "123456", 10)
    body = message.get_content()
    assert message["To"] == STAFF and message["Subject"] == "Your iHub sign-in code"
    assert "123456" in body and "10 minutes" in body and "used once" in body
