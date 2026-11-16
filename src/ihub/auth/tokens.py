"""Tokens (ADR-010): JWT access tokens, rotating refresh tokens and signed OAuth flow state.

- Access token: HS256 JWT, 15 minutes, carries the user's id, email and role.
- Refresh token: 256 random bits, stored only as a SHA-256 hash, rotated on every use.
  Presenting a rotated token after the grace period revokes the whole family (theft signal).
- OAuth flow: the state, nonce and PKCE verifier of a Google sign-in, signed so the
  front end can hold them in a cookie without being able to change them.

Expiry is checked against the injected clock, so tests control time.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import jwt

from ihub.auth.config import AuthConfig, Clock
from ihub.auth.errors import InvalidRequestError, InvalidTokenError
from ihub.auth.models import Principal, RefreshTokenRecord, User
from ihub.auth.rbac import Role
from ihub.auth.store import RefreshTokenRepository

ISSUER = "ihub-api"
ACCESS_AUDIENCE = "ihub-web"
FLOW_AUDIENCE = "ihub-oauth-flow"
_ALGORITHM = "HS256"
_DECODE_OPTIONS = {"verify_exp": False, "verify_iat": False, "verify_nbf": False}

ROTATED = "rotated"
SIGNED_OUT = "signed_out"
REUSE_DETECTED = "reuse_detected"
USER_DEACTIVATED = "user_deactivated"


class RefreshTokenReuseError(InvalidTokenError):
    """A rotated refresh token came back after the grace period; its family is revoked."""

    def __init__(self, user_id: str) -> None:
        super().__init__()
        self.user_id = user_id


@dataclass(frozen=True)
class IssuedRefreshToken:
    """A new refresh token (the only time it exists in clear) and when it expires."""

    token: str
    expires_at: datetime


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def pkce_pair() -> tuple[str, str]:
    """A PKCE code verifier and its S256 challenge (RFC 7636)."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class TokenService:
    """Issues and checks every token. Holds no state beyond the refresh-token repository."""

    def __init__(
        self, config: AuthConfig, refresh_tokens: RefreshTokenRepository, clock: Clock
    ) -> None:
        self._config = config
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._access_key = config.key("access-token")
        self._flow_key = config.key("oauth-flow")

    # Access tokens ---------------------------------------------------------------------

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._config.access_ttl.total_seconds())

    def access_token(self, user: User) -> str:
        now = self._clock()
        claims = {
            "iss": ISSUER,
            "aud": ACCESS_AUDIENCE,
            "sub": user.user_id,
            "email": user.email,
            "role": user.role.value,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + self._config.access_ttl).timestamp()),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(claims, self._access_key, algorithm=_ALGORITHM)

    def verify_access_token(self, token: str) -> Principal:
        """The caller behind a valid access token; InvalidTokenError otherwise."""
        try:
            claims = jwt.decode(
                token,
                self._access_key,
                algorithms=[_ALGORITHM],
                audience=ACCESS_AUDIENCE,
                issuer=ISSUER,
                options={**_DECODE_OPTIONS, "require": ["exp", "iat", "sub", "jti"]},
            )
            role = Role(claims["role"])
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise InvalidTokenError() from exc
        if claims.get("typ") != "access" or claims["exp"] <= self._clock().timestamp():
            raise InvalidTokenError()
        return Principal(user_id=str(claims["sub"]), email=str(claims["email"]), role=role)

    # Refresh tokens --------------------------------------------------------------------

    def start_session(self, user_id: str) -> IssuedRefreshToken:
        """The first refresh token of a new sign-in (a new family)."""
        now = self._clock()
        return self._issue(user_id, family_id=uuid.uuid4().hex, family_started_at=now, now=now)

    def check_refresh(self, token: str) -> RefreshTokenRecord:
        """The record behind a refresh token that may be rotated; InvalidTokenError otherwise.

        A token rotated less than ``refresh_reuse_grace`` ago is still accepted, so parallel
        requests that raced to refresh do not sign the user out. Later reuse revokes the
        family and raises RefreshTokenReuseError.
        """
        record = self._refresh_tokens.get(hash_refresh_token(token))
        if record is None:
            raise InvalidTokenError()
        now = self._clock()
        if record.revoked_at is not None:
            within_grace = (
                record.revoked_reason == ROTATED
                and now - record.revoked_at <= self._config.refresh_reuse_grace
            )
            if within_grace:
                return record
            if record.revoked_reason == ROTATED:
                self._refresh_tokens.revoke_family(record.family_id, now, REUSE_DETECTED)
                raise RefreshTokenReuseError(record.user_id)
            raise InvalidTokenError()
        if now >= record.expires_at or now >= self._session_end(record.family_started_at):
            raise InvalidTokenError()
        return record

    def rotate(self, record: RefreshTokenRecord) -> IssuedRefreshToken:
        """Replace a checked token with a new one in the same family."""
        now = self._clock()
        self._refresh_tokens.revoke(record.token_hash, now, ROTATED)
        return self._issue(
            record.user_id,
            family_id=record.family_id,
            family_started_at=record.family_started_at,
            now=now,
        )

    def end_session(self, token: str) -> RefreshTokenRecord | None:
        """Sign out: revoke the token's whole family. Unknown tokens are ignored."""
        record = self._refresh_tokens.get(hash_refresh_token(token))
        if record is not None:
            self._refresh_tokens.revoke_family(record.family_id, self._clock(), SIGNED_OUT)
        return record

    def revoke_family(self, family_id: str, reason: str) -> None:
        self._refresh_tokens.revoke_family(family_id, self._clock(), reason)

    def revoke_user(self, user_id: str, reason: str) -> None:
        self._refresh_tokens.revoke_user(user_id, self._clock(), reason)

    def _session_end(self, family_started_at: datetime) -> datetime:
        return family_started_at + self._config.session_max_age

    def _issue(
        self, user_id: str, *, family_id: str, family_started_at: datetime, now: datetime
    ) -> IssuedRefreshToken:
        token = secrets.token_urlsafe(32)
        expires_at = min(now + self._config.refresh_ttl, self._session_end(family_started_at))
        self._refresh_tokens.add(
            RefreshTokenRecord(
                token_hash=hash_refresh_token(token),
                user_id=user_id,
                family_id=family_id,
                family_started_at=family_started_at,
                issued_at=now,
                expires_at=expires_at,
            )
        )
        return IssuedRefreshToken(token=token, expires_at=expires_at)

    # OAuth flow state ------------------------------------------------------------------

    @property
    def flow_ttl_seconds(self) -> int:
        return int(self._config.oauth_flow_ttl.total_seconds())

    def sign_flow(self, data: dict[str, str]) -> str:
        now = self._clock()
        claims = {
            **data,
            "iss": ISSUER,
            "aud": FLOW_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + self._config.oauth_flow_ttl).timestamp()),
        }
        return jwt.encode(claims, self._flow_key, algorithm=_ALGORITHM)

    def read_flow(self, flow: str) -> dict[str, Any]:
        """The data of an unexpired, untampered flow; InvalidRequestError otherwise."""
        message = "This sign-in attempt has expired or is not valid. Start again."
        try:
            claims = jwt.decode(
                flow,
                self._flow_key,
                algorithms=[_ALGORITHM],
                audience=FLOW_AUDIENCE,
                issuer=ISSUER,
                options={**_DECODE_OPTIONS, "require": ["exp"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidRequestError(message, reason="invalid_flow") from exc
        if claims["exp"] <= self._clock().timestamp():
            raise InvalidRequestError(message, reason="expired_flow")
        return claims
