"""Firestore implementation of the authentication store, for production (ADR-009).

Cloud Run's disk is temporary, so users, refresh tokens, email codes, audit events and
profile photos live in Firestore (Native mode). Credentials come from the runtime service
account (no keys). Queries use only single-field equality filters and single-field
ordering, so Firestore's automatic indexes are enough: no index set-up is needed.

Times are stored as UTC ISO text, the same format as the SQLite store, so they sort
correctly. A Firestore document holds at most 1 MiB, so photos are split into chunks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from ihub.auth.models import (
    AuthEvent,
    Avatar,
    EmailChallenge,
    RefreshTokenRecord,
    User,
    UserStatus,
)
from ihub.auth.rbac import Role

USERS = "auth_users"
REFRESH_TOKENS = "auth_refresh_tokens"
EMAIL_CHALLENGES = "auth_email_challenges"
EVENTS = "auth_events"
AVATARS = "auth_avatars"
CHUNKS = "chunks"
CHUNK_BYTES = 900_000  # below Firestore's 1 MiB document limit


def _ts(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _equal(field: str, value: Any) -> FieldFilter:
    return FieldFilter(field, "==", value)


class FirestoreUserRepository:
    """Users, one document per ``user_id``."""

    def __init__(self, client: Any) -> None:
        self._col = client.collection(USERS)

    @staticmethod
    def _user(data: dict[str, Any] | None) -> User | None:
        if data is None:
            return None
        return User(
            user_id=data["user_id"],
            email=data["email"],
            name=data.get("name"),
            role=Role(data["role"]),
            status=UserStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_sign_in_at=_dt(data.get("last_sign_in_at")),
            phone=data.get("phone"),
            avatar_updated_at=_dt(data.get("avatar_updated_at")),
        )

    @staticmethod
    def _data(user: User) -> dict[str, Any]:
        return {
            "user_id": user.user_id,
            "email": user.email.lower(),
            "name": user.name,
            "role": user.role.value,
            "status": user.status.value,
            "created_at": _ts(user.created_at),
            "last_sign_in_at": _ts(user.last_sign_in_at),
            "phone": user.phone,
            "avatar_updated_at": _ts(user.avatar_updated_at),
        }

    def get(self, user_id: str) -> User | None:
        return self._user(self._col.document(user_id).get().to_dict())

    def get_by_email(self, email: str) -> User | None:
        for snapshot in self._col.where(filter=_equal("email", email.lower())).stream():
            return self._user(snapshot.to_dict())
        return None

    def add(self, user: User) -> None:
        if self.get_by_email(user.email) is not None:
            raise ValueError(f"A user with email {user.email.lower()} already exists.")
        self._col.document(user.user_id).create(self._data(user))

    def update(self, user: User) -> None:
        data = self._data(user)
        data.pop("created_at")
        self._col.document(user.user_id).update(data)

    def list_all(self) -> list[User]:
        users = [self._user(s.to_dict()) for s in self._col.stream()]
        return sorted((u for u in users if u is not None), key=lambda u: u.email)


class FirestoreRefreshTokenRepository:
    """Refresh-token records, one document per token hash."""

    def __init__(self, client: Any) -> None:
        self._col = client.collection(REFRESH_TOKENS)

    def add(self, record: RefreshTokenRecord) -> None:
        self._col.document(record.token_hash).create(
            {
                "token_hash": record.token_hash,
                "user_id": record.user_id,
                "family_id": record.family_id,
                "family_started_at": _ts(record.family_started_at),
                "issued_at": _ts(record.issued_at),
                "expires_at": _ts(record.expires_at),
                "revoked_at": _ts(record.revoked_at),
                "revoked_reason": record.revoked_reason,
            }
        )

    def get(self, token_hash: str) -> RefreshTokenRecord | None:
        data = self._col.document(token_hash).get().to_dict()
        if data is None:
            return None
        return RefreshTokenRecord(
            token_hash=data["token_hash"],
            user_id=data["user_id"],
            family_id=data["family_id"],
            family_started_at=datetime.fromisoformat(data["family_started_at"]),
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            revoked_at=_dt(data.get("revoked_at")),
            revoked_reason=data.get("revoked_reason"),
        )

    def _revoke(self, snapshots: Any, at: datetime, reason: str) -> None:
        for snapshot in snapshots:
            data = snapshot.to_dict()
            if data is not None and data.get("revoked_at") is None:
                snapshot.reference.update({"revoked_at": _ts(at), "revoked_reason": reason})

    def revoke(self, token_hash: str, at: datetime, reason: str) -> None:
        snapshot = self._col.document(token_hash).get()
        if snapshot.exists:
            self._revoke([snapshot], at, reason)

    def revoke_family(self, family_id: str, at: datetime, reason: str) -> None:
        self._revoke(self._col.where(filter=_equal("family_id", family_id)).stream(), at, reason)

    def revoke_user(self, user_id: str, at: datetime, reason: str) -> None:
        self._revoke(self._col.where(filter=_equal("user_id", user_id)).stream(), at, reason)


class FirestoreEmailChallengeRepository:
    """Email sign-in challenges, one document per challenge."""

    def __init__(self, client: Any) -> None:
        self._col = client.collection(EMAIL_CHALLENGES)

    @staticmethod
    def _challenge(data: dict[str, Any]) -> EmailChallenge:
        return EmailChallenge(
            challenge_id=data["challenge_id"],
            email=data["email"],
            code_hash=data["code_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            attempts=data["attempts"],
            consumed_at=_dt(data.get("consumed_at")),
        )

    def _for(self, email: str) -> list[dict[str, Any]]:
        snapshots = self._col.where(filter=_equal("email", email.lower())).stream()
        rows = [d for s in snapshots if (d := s.to_dict()) is not None]
        return sorted(rows, key=lambda d: (d["created_at"], d.get("seq", 0)))

    def add(self, challenge: EmailChallenge) -> None:
        self._col.document(challenge.challenge_id).create(
            {
                "challenge_id": challenge.challenge_id,
                "email": challenge.email.lower(),
                "code_hash": challenge.code_hash,
                "created_at": _ts(challenge.created_at),
                "expires_at": _ts(challenge.expires_at),
                "attempts": challenge.attempts,
                "consumed_at": _ts(challenge.consumed_at),
                "seq": len(self._for(challenge.email)),
            }
        )

    def update(self, challenge: EmailChallenge) -> None:
        self._col.document(challenge.challenge_id).update(
            {"attempts": challenge.attempts, "consumed_at": _ts(challenge.consumed_at)}
        )

    def latest(self, email: str) -> EmailChallenge | None:
        rows = self._for(email)
        return self._challenge(rows[-1]) if rows else None

    def created_since(self, email: str, since: datetime) -> list[datetime]:
        floor = _ts(since) or ""
        return [
            datetime.fromisoformat(d["created_at"])
            for d in self._for(email)
            if d["created_at"] >= floor
        ]


class FirestoreAuditLog:
    """Audit events, newest first by time."""

    def __init__(self, client: Any) -> None:
        self._col = client.collection(EVENTS)

    def record(self, event: AuthEvent) -> None:
        self._col.add(
            {
                "kind": event.kind,
                "occurred_at": _ts(event.occurred_at),
                "user_id": event.user_id,
                "actor_id": event.actor_id,
                "detail": event.detail,
            }
        )

    def recent(self, limit: int = 100) -> list[AuthEvent]:
        query = self._col.order_by("occurred_at", direction="DESCENDING").limit(limit)
        events = []
        for snapshot in query.stream():
            data = snapshot.to_dict()
            events.append(
                AuthEvent(
                    kind=data["kind"],
                    occurred_at=datetime.fromisoformat(data["occurred_at"]),
                    user_id=data.get("user_id"),
                    actor_id=data.get("actor_id"),
                    detail=data.get("detail"),
                )
            )
        return events


class FirestoreAvatarRepository:
    """Profile photos: a document per user, with the bytes split into chunk documents."""

    def __init__(self, client: Any) -> None:
        self._col = client.collection(AVATARS)

    def get(self, user_id: str) -> Avatar | None:
        doc = self._col.document(user_id)
        data = doc.get().to_dict()
        if data is None:
            return None
        chunks = doc.collection(CHUNKS)
        parts = [chunks.document(str(i)).get().to_dict() for i in range(data["n_chunks"])]
        if any(part is None for part in parts):
            return None
        return Avatar(
            content_type=data["content_type"],
            data=b"".join(part["data"] for part in parts if part is not None),
            updated_at=_dt(data.get("updated_at")),
        )

    def put(self, user_id: str, avatar: Avatar) -> None:
        self.delete(user_id)
        doc = self._col.document(user_id)
        chunks = [avatar.data[i : i + CHUNK_BYTES] for i in range(0, len(avatar.data), CHUNK_BYTES)]
        for i, chunk in enumerate(chunks):
            doc.collection(CHUNKS).document(str(i)).set({"data": chunk})
        doc.set(
            {
                "content_type": avatar.content_type,
                "updated_at": _ts(avatar.updated_at),
                "n_chunks": len(chunks),
            }
        )

    def delete(self, user_id: str) -> None:
        doc = self._col.document(user_id)
        for snapshot in doc.collection(CHUNKS).stream():
            snapshot.reference.delete()
        doc.delete()


class FirestoreAuthStore:
    """All authentication repositories over one Firestore database."""

    def __init__(self, client: Any) -> None:
        self._users = FirestoreUserRepository(client)
        self._refresh_tokens = FirestoreRefreshTokenRepository(client)
        self._email_challenges = FirestoreEmailChallengeRepository(client)
        self._audit = FirestoreAuditLog(client)
        self._avatars = FirestoreAvatarRepository(client)

    @classmethod
    def connect(cls, database: str = "(default)") -> FirestoreAuthStore:
        """Uses the runtime's own Google credentials (Workload Identity, no keys)."""
        from google.cloud import firestore

        return cls(firestore.Client(database=database))

    @property
    def users(self) -> FirestoreUserRepository:
        return self._users

    @property
    def refresh_tokens(self) -> FirestoreRefreshTokenRepository:
        return self._refresh_tokens

    @property
    def email_challenges(self) -> FirestoreEmailChallengeRepository:
        return self._email_challenges

    @property
    def audit(self) -> FirestoreAuditLog:
        return self._audit

    @property
    def avatars(self) -> FirestoreAvatarRepository:
        return self._avatars
