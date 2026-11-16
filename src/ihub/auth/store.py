"""Repository interfaces for authentication data (ADR-009, ADR-010).

The service depends on these small protocols, not on a database, so the SQLite store used
in tests and development and the Firestore store used in production are interchangeable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ihub.auth.models import AuthEvent, EmailChallenge, RefreshTokenRecord, User


class UserRepository(Protocol):
    """Registered users, keyed by ``user_id`` and unique by lower-case email."""

    def get(self, user_id: str) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: User) -> None: ...

    def update(self, user: User) -> None: ...

    def list_all(self) -> list[User]: ...


class RefreshTokenRepository(Protocol):
    """Refresh-token records, keyed by the token's hash."""

    def add(self, record: RefreshTokenRecord) -> None: ...

    def get(self, token_hash: str) -> RefreshTokenRecord | None: ...

    def revoke(self, token_hash: str, at: datetime, reason: str) -> None: ...

    def revoke_family(self, family_id: str, at: datetime, reason: str) -> None: ...

    def revoke_user(self, user_id: str, at: datetime, reason: str) -> None: ...


class EmailChallengeRepository(Protocol):
    """Email sign-in challenges; the newest one per address is the live one."""

    def add(self, challenge: EmailChallenge) -> None: ...

    def update(self, challenge: EmailChallenge) -> None: ...

    def latest(self, email: str) -> EmailChallenge | None: ...

    def created_since(self, email: str, since: datetime) -> list[datetime]: ...


class AuditLog(Protocol):
    """Append-only record of sign-ins and access changes."""

    def record(self, event: AuthEvent) -> None: ...

    def recent(self, limit: int = 100) -> list[AuthEvent]: ...


class AuthStore(Protocol):
    """Everything authentication stores, one repository per kind of record."""

    @property
    def users(self) -> UserRepository: ...

    @property
    def refresh_tokens(self) -> RefreshTokenRepository: ...

    @property
    def email_challenges(self) -> EmailChallengeRepository: ...

    @property
    def audit(self) -> AuditLog: ...
