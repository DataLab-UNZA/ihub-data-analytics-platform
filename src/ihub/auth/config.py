"""Authentication configuration, key derivation and the UNZA email rule (ADR-010)."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ihub.auth.errors import InvalidEmailError

MIN_SECRET_BYTES = 32
MAX_EMAIL_LENGTH = 254


Clock = Callable[[], datetime]
"""Returns the current time (timezone-aware UTC)."""


def utc_now() -> datetime:
    """The default clock. Services take a clock argument so tests can move time."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class AuthConfig:
    """Settings the authentication services need. Lifetimes follow ADR-010."""

    secret: bytes = field(repr=False)
    allowed_domain: str = "unza.ac.zm"
    environment: str = "production"
    public_url: str | None = None
    bootstrap_admins: frozenset[str] = frozenset()
    access_ttl: timedelta = timedelta(minutes=15)
    refresh_ttl: timedelta = timedelta(days=7)
    session_max_age: timedelta = timedelta(days=30)
    refresh_reuse_grace: timedelta = timedelta(seconds=20)
    oauth_flow_ttl: timedelta = timedelta(minutes=10)
    email_code_ttl: timedelta = timedelta(minutes=10)
    email_code_max_attempts: int = 5
    email_resend_interval: timedelta = timedelta(seconds=30)
    email_max_per_hour: int = 5

    def __post_init__(self) -> None:
        if len(self.secret) < MIN_SECRET_BYTES:
            raise ValueError(f"The auth secret must be at least {MIN_SECRET_BYTES} bytes.")
        object.__setattr__(self, "allowed_domain", self.allowed_domain.strip().lower())

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def google_redirect_uri(self) -> str | None:
        """Where Google sends the browser back to (the Next.js callback route)."""
        if not self.public_url:
            return None
        return f"{self.public_url.rstrip('/')}/auth/google/callback"

    def key(self, purpose: str) -> bytes:
        """A separate 32-byte key per purpose, derived from the one secret (HMAC-SHA256)."""
        return hmac.new(self.secret, f"ihub/{purpose}".encode(), hashlib.sha256).digest()

    def normalise_email(self, raw: str) -> str:
        """Lower-case, trimmed address at the allowed domain; otherwise InvalidEmailError."""
        email = raw.strip().lower()
        local, at, domain = email.rpartition("@")
        well_formed = (
            at == "@"
            and local
            and "@" not in local
            and len(email) <= MAX_EMAIL_LENGTH
            and not any(char.isspace() for char in email)
        )
        if not well_formed or domain != self.allowed_domain:
            raise InvalidEmailError(
                f"Use your UNZA email address (ending @{self.allowed_domain}).",
                reason="wrong_domain" if well_formed else "malformed_email",
            )
        return email


def parse_email_list(value: str) -> frozenset[str]:
    """Comma-separated addresses, trimmed and lower-cased (for IHUB_BOOTSTRAP_ADMINS)."""
    return frozenset(item.strip().lower() for item in value.split(",") if item.strip())
