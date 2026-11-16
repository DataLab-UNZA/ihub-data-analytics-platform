"""SQLite implementation of the authentication store, for tests and local development.

Not for production on Cloud Run, where the disk is temporary (ADR-009, ADR-010): the
factory refuses it there. Each call opens its own connection, so the store is safe to use
from FastAPI's thread pool.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from ihub.auth.models import (
    AuthEvent,
    EmailChallenge,
    RefreshTokenRecord,
    User,
    UserStatus,
)
from ihub.auth.rbac import Role

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_sign_in_at TEXT
);
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    family_id TEXT NOT NULL,
    family_started_at TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    revoked_reason TEXT
);
CREATE INDEX IF NOT EXISTS refresh_tokens_family ON refresh_tokens (family_id);
CREATE INDEX IF NOT EXISTS refresh_tokens_user ON refresh_tokens (user_id);
CREATE TABLE IF NOT EXISTS email_challenges (
    challenge_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    consumed_at TEXT
);
CREATE INDEX IF NOT EXISTS email_challenges_email ON email_challenges (email, created_at);
CREATE TABLE IF NOT EXISTS auth_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    user_id TEXT,
    actor_id TEXT,
    detail TEXT
);
"""


def _ts(value: datetime | None) -> str | None:
    """UTC with a fixed format, so stored times also sort correctly as text."""
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _required_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class _Database:
    """Opens a short-lived connection per operation; commits or rolls back on exit."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(_SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()


class SqliteUserRepository:
    """Users in the ``users`` table."""

    def __init__(self, db: _Database) -> None:
        self._db = db

    @staticmethod
    def _row(row: sqlite3.Row | None) -> User | None:
        if row is None:
            return None
        return User(
            user_id=row["user_id"],
            email=row["email"],
            name=row["name"],
            role=Role(row["role"]),
            status=UserStatus(row["status"]),
            created_at=_required_dt(row["created_at"]),
            last_sign_in_at=_dt(row["last_sign_in_at"]),
        )

    def get(self, user_id: str) -> User | None:
        with self._db.connect() as con:
            row = con.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return self._row(row)

    def get_by_email(self, email: str) -> User | None:
        with self._db.connect() as con:
            row = con.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return self._row(row)

    def add(self, user: User) -> None:
        with self._db.connect() as con:
            con.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user.user_id,
                    user.email.lower(),
                    user.name,
                    user.role.value,
                    user.status.value,
                    _ts(user.created_at),
                    _ts(user.last_sign_in_at),
                ),
            )

    def update(self, user: User) -> None:
        with self._db.connect() as con:
            con.execute(
                "UPDATE users SET email = ?, name = ?, role = ?, status = ?, last_sign_in_at = ? "
                "WHERE user_id = ?",
                (
                    user.email.lower(),
                    user.name,
                    user.role.value,
                    user.status.value,
                    _ts(user.last_sign_in_at),
                    user.user_id,
                ),
            )

    def list_all(self) -> list[User]:
        with self._db.connect() as con:
            rows = con.execute("SELECT * FROM users ORDER BY email").fetchall()
        return [user for row in rows if (user := self._row(row)) is not None]


class SqliteRefreshTokenRepository:
    """Refresh-token records in the ``refresh_tokens`` table."""

    def __init__(self, db: _Database) -> None:
        self._db = db

    def add(self, record: RefreshTokenRecord) -> None:
        with self._db.connect() as con:
            con.execute(
                "INSERT INTO refresh_tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.token_hash,
                    record.user_id,
                    record.family_id,
                    _ts(record.family_started_at),
                    _ts(record.issued_at),
                    _ts(record.expires_at),
                    _ts(record.revoked_at),
                    record.revoked_reason,
                ),
            )

    def get(self, token_hash: str) -> RefreshTokenRecord | None:
        with self._db.connect() as con:
            row = con.execute(
                "SELECT * FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
            ).fetchone()
        if row is None:
            return None
        return RefreshTokenRecord(
            token_hash=row["token_hash"],
            user_id=row["user_id"],
            family_id=row["family_id"],
            family_started_at=_required_dt(row["family_started_at"]),
            issued_at=_required_dt(row["issued_at"]),
            expires_at=_required_dt(row["expires_at"]),
            revoked_at=_dt(row["revoked_at"]),
            revoked_reason=row["revoked_reason"],
        )

    def _revoke_where(self, clause: str, value: str, at: datetime, reason: str) -> None:
        with self._db.connect() as con:
            con.execute(
                "UPDATE refresh_tokens SET revoked_at = ?, revoked_reason = ? "
                f"WHERE {clause} = ? AND revoked_at IS NULL",
                (_ts(at), reason, value),
            )

    def revoke(self, token_hash: str, at: datetime, reason: str) -> None:
        self._revoke_where("token_hash", token_hash, at, reason)

    def revoke_family(self, family_id: str, at: datetime, reason: str) -> None:
        self._revoke_where("family_id", family_id, at, reason)

    def revoke_user(self, user_id: str, at: datetime, reason: str) -> None:
        self._revoke_where("user_id", user_id, at, reason)


class SqliteEmailChallengeRepository:
    """Email sign-in challenges in the ``email_challenges`` table."""

    def __init__(self, db: _Database) -> None:
        self._db = db

    def add(self, challenge: EmailChallenge) -> None:
        with self._db.connect() as con:
            con.execute(
                "INSERT INTO email_challenges VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    challenge.challenge_id,
                    challenge.email.lower(),
                    challenge.code_hash,
                    _ts(challenge.created_at),
                    _ts(challenge.expires_at),
                    challenge.attempts,
                    _ts(challenge.consumed_at),
                ),
            )

    def update(self, challenge: EmailChallenge) -> None:
        with self._db.connect() as con:
            con.execute(
                "UPDATE email_challenges SET attempts = ?, consumed_at = ? WHERE challenge_id = ?",
                (challenge.attempts, _ts(challenge.consumed_at), challenge.challenge_id),
            )

    def latest(self, email: str) -> EmailChallenge | None:
        with self._db.connect() as con:
            row = con.execute(
                "SELECT * FROM email_challenges WHERE email = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (email.lower(),),
            ).fetchone()
        if row is None:
            return None
        return EmailChallenge(
            challenge_id=row["challenge_id"],
            email=row["email"],
            code_hash=row["code_hash"],
            created_at=_required_dt(row["created_at"]),
            expires_at=_required_dt(row["expires_at"]),
            attempts=row["attempts"],
            consumed_at=_dt(row["consumed_at"]),
        )

    def created_since(self, email: str, since: datetime) -> list[datetime]:
        with self._db.connect() as con:
            rows = con.execute(
                "SELECT created_at FROM email_challenges WHERE email = ? AND created_at >= ? "
                "ORDER BY created_at",
                (email.lower(), _ts(since)),
            ).fetchall()
        return [_required_dt(row["created_at"]) for row in rows]


class SqliteAuditLog:
    """Audit events in the ``auth_events`` table."""

    def __init__(self, db: _Database) -> None:
        self._db = db

    def record(self, event: AuthEvent) -> None:
        with self._db.connect() as con:
            con.execute(
                "INSERT INTO auth_events (kind, occurred_at, user_id, actor_id, detail) "
                "VALUES (?, ?, ?, ?, ?)",
                (event.kind, _ts(event.occurred_at), event.user_id, event.actor_id, event.detail),
            )

    def recent(self, limit: int = 100) -> list[AuthEvent]:
        with self._db.connect() as con:
            rows = con.execute(
                "SELECT * FROM auth_events ORDER BY event_id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            AuthEvent(
                kind=row["kind"],
                occurred_at=_required_dt(row["occurred_at"]),
                user_id=row["user_id"],
                actor_id=row["actor_id"],
                detail=row["detail"],
            )
            for row in rows
        ]


class SqliteAuthStore:
    """All authentication repositories over one SQLite file."""

    def __init__(self, path: Path) -> None:
        db = _Database(path)
        self._users = SqliteUserRepository(db)
        self._refresh_tokens = SqliteRefreshTokenRepository(db)
        self._email_challenges = SqliteEmailChallengeRepository(db)
        self._audit = SqliteAuditLog(db)

    @property
    def users(self) -> SqliteUserRepository:
        return self._users

    @property
    def refresh_tokens(self) -> SqliteRefreshTokenRepository:
        return self._refresh_tokens

    @property
    def email_challenges(self) -> SqliteEmailChallengeRepository:
        return self._email_challenges

    @property
    def audit(self) -> SqliteAuditLog:
        return self._audit
