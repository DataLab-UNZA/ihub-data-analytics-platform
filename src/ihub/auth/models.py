"""The records authentication keeps: users, refresh tokens, email challenges, audit events.

All times are timezone-aware UTC. No record holds a token or code in clear text: refresh
tokens and email codes are stored only as hashes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from ihub.auth.rbac import Permission, Role, permissions_for


class UserStatus(StrEnum):
    """Whether a user may sign in."""

    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class SignInMethod(StrEnum):
    """How a user proved they own their email address."""

    GOOGLE = "google"
    EMAIL_CODE = "email_code"


@dataclass(frozen=True)
class User:
    """A registered member of staff. ``email`` is lower-case and unique."""

    user_id: str
    email: str
    name: str | None
    role: Role
    status: UserStatus
    created_at: datetime
    last_sign_in_at: datetime | None = None
    phone: str | None = None
    avatar_updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status is UserStatus.ACTIVE

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.role)


@dataclass(frozen=True)
class Principal:
    """The caller of an API request, as proven by a valid access token."""

    user_id: str
    email: str
    role: Role

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.role)

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions


@dataclass(frozen=True)
class RefreshTokenRecord:
    """One refresh token (by hash). Tokens of one sign-in share a ``family_id``."""

    token_hash: str
    user_id: str
    family_id: str
    family_started_at: datetime
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    revoked_reason: str | None = None


@dataclass(frozen=True)
class EmailChallenge:
    """A one-time sign-in code sent to ``email`` (stored as an HMAC, never in clear)."""

    challenge_id: str
    email: str
    code_hash: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    consumed_at: datetime | None = None


@dataclass(frozen=True)
class Avatar:
    """A profile photo: checked image bytes and their media type."""

    content_type: str
    data: bytes = field(repr=False)
    updated_at: datetime | None = None


@dataclass(frozen=True)
class AuthEvent:
    """An audit record. ``detail`` never contains tokens or codes."""

    kind: str
    occurred_at: datetime
    user_id: str | None = None
    actor_id: str | None = None
    detail: str | None = None
