"""The Firestore user store behaves like the SQLite one (ADR-009), using an in-memory fake."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ihub.auth.errors import AuthNotConfiguredError
from ihub.auth.factory import build_auth_service
from ihub.auth.firestore_store import CHUNK_BYTES, FirestoreAuthStore
from ihub.auth.models import Avatar, EmailChallenge, RefreshTokenRecord
from ihub.auth.sqlite_store import SqliteAuthStore
from ihub.settings import Settings
from tests.auth_helpers import ADMIN, STAFF, make_harness
from tests.fake_firestore import FakeFirestore

T0 = datetime(2026, 11, 17, 8, 0, tzinfo=UTC)


@pytest.fixture(params=["sqlite", "firestore"])
def store(request: pytest.FixtureRequest, tmp_path: Path):
    if request.param == "sqlite":
        return SqliteAuthStore(tmp_path / "auth.sqlite")
    return FirestoreAuthStore(FakeFirestore())


def test_email_code_sign_in_end_to_end(store, tmp_path: Path) -> None:
    h = make_harness(tmp_path, store=store)
    h.service.request_email_code(STAFF)
    result = h.service.finish_email_code(email=STAFF, code=h.email.last_code)
    assert result.user.email == STAFF
    assert store.users.get_by_email(STAFF.upper()).user_id == result.user.user_id
    refreshed = h.service.refresh(result.refresh_token)
    assert refreshed.access_token
    h.service.request_email_code(ADMIN)
    h.service.finish_email_code(email=ADMIN, code=h.email.last_code)
    assert [u.email for u in store.users.list_all()] == sorted([STAFF, ADMIN])
    assert store.audit.recent(limit=1)


def test_refresh_tokens_revoke_by_family_and_user(store) -> None:
    for i, family in enumerate(["f1", "f1", "f2"]):
        store.refresh_tokens.add(
            RefreshTokenRecord(f"h{i}", "u1", family, T0, T0, T0 + timedelta(days=1))
        )
    store.refresh_tokens.revoke_family("f1", T0, "reuse")
    assert store.refresh_tokens.get("h0").revoked_reason == "reuse"
    assert store.refresh_tokens.get("h2").revoked_at is None
    store.refresh_tokens.revoke_user("u1", T0 + timedelta(hours=1), "signed out")
    assert store.refresh_tokens.get("h0").revoked_reason == "reuse"
    assert store.refresh_tokens.get("h2").revoked_reason == "signed out"
    assert store.refresh_tokens.get("missing") is None


def test_email_challenges_latest_and_since(store) -> None:
    for i in range(3):
        at = T0 + timedelta(minutes=i)
        store.email_challenges.add(
            EmailChallenge(f"c{i}", "A@unza.ac.zm", "x", at, at + timedelta(minutes=10))
        )
    assert store.email_challenges.latest("a@unza.ac.zm").challenge_id == "c2"
    assert len(store.email_challenges.created_since("a@unza.ac.zm", T0 + timedelta(minutes=1))) == 2


def test_large_photos_are_split_below_the_document_limit(store) -> None:
    data = bytes(range(256)) * ((CHUNK_BYTES * 2) // 256 + 10)
    store.avatars.put("u1", Avatar("image/png", data, T0))
    assert store.avatars.get("u1").data == data
    store.avatars.put("u1", Avatar("image/jpeg", b"small", T0))
    assert store.avatars.get("u1").data == b"small"
    store.avatars.delete("u1")
    assert store.avatars.get("u1") is None


def test_factory_refuses_unknown_store(tmp_path: Path) -> None:
    s = Settings(
        _env_file=None,
        ihub_auth_db_path=tmp_path / "a.sqlite",
        ihub_auth_secret="x" * 40,
        ihub_auth_store="mystery",
    )
    with pytest.raises(AuthNotConfiguredError, match="unknown IHUB_AUTH_STORE"):
        build_auth_service(s)
