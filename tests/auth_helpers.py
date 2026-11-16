"""Helpers for the authentication tests (ADR-010). Nothing here calls Google or sends mail.

- ``FakeClock``: time the tests can move forward.
- ``RecordingEmailSender``: keeps the codes it was asked to send.
- ``FakeGoogle``: plays Google's token endpoint. It checks the PKCE verifier against the
  challenge in the authorisation URL and returns ID tokens signed with a local RSA key.
- ``make_harness``: an ``AuthService`` over a temporary SQLite store with all of the above.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from ihub.auth.config import AuthConfig
from ihub.auth.email_codes import EmailCodeService
from ihub.auth.google import GoogleOAuthClient
from ihub.auth.service import AuthService, SignInResult
from ihub.auth.sqlite_store import SqliteAuthStore
from ihub.auth.tokens import TokenService

DOMAIN = "unza.ac.zm"
SECRET = b"test-secret-of-at-least-thirty-two-bytes"
CLIENT_ID = "test-client.apps.googleusercontent.com"
PUBLIC_URL = "https://ihub.example.test"
STAFF = "test.staff@unza.ac.zm"
ADMIN = "test.admin@unza.ac.zm"
DROP = object()
"""Pass as a claim value to ``FakeGoogle.id_token`` to leave the claim out."""


class FakeClock:
    """A clock that starts now (whole seconds) and moves only when told to."""

    def __init__(self) -> None:
        self.now = datetime.now(UTC).replace(microsecond=0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


class RecordingEmailSender:
    """Records (address, code) instead of sending email."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_sign_in_code(self, to: str, code: str, valid_minutes: int) -> None:
        self.sent.append((to, code))

    @property
    def last_code(self) -> str:
        return self.sent[-1][1]


@lru_cache(maxsize=2)
def rsa_key(seed: int = 0) -> rsa.RSAPrivateKey:
    """A 2048-bit RSA key per ``seed``, generated once per test run."""
    del seed  # only distinguishes cache entries
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class FakeGoogle:
    """Google's token endpoint and signing key, for one sign-in at a time."""

    private_key: rsa.RSAPrivateKey = field(default_factory=rsa_key)
    claims: dict[str, Any] = field(default_factory=dict)
    nonce: str | None = None
    code_challenge: str | None = None
    token_requests: list[dict[str, list[str]]] = field(default_factory=list)

    def browser_visits(self, authorization_url: str) -> str:
        """Read what the browser would carry to Google; returns the state Google echoes back."""
        query = parse_qs(urlparse(authorization_url).query)
        self.nonce = query["nonce"][0]
        self.code_challenge = query["code_challenge"][0]
        return query["state"][0]

    def id_token(self, *, key: rsa.RSAPrivateKey | None = None, **overrides: Any) -> str:
        now = int(datetime.now(UTC).timestamp())
        claims: dict[str, Any] = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": "100000000000000000001",
            "email": STAFF,
            "email_verified": True,
            "hd": DOMAIN,
            "name": "Test Staff",
            "iat": now,
            "exp": now + 3600,
            "nonce": self.nonce,
        }
        claims.update(overrides)
        claims = {name: value for name, value in claims.items() if value is not DROP}
        return jwt.encode(claims, key or self.private_key, algorithm="RS256")

    def token_endpoint(self, request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        self.token_requests.append(form)
        verifier = form["code_verifier"][0]
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if form.get("code") != ["good-code"] or challenge != self.code_challenge:
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(200, json={"id_token": self.id_token(**self.claims)})

    def client(self) -> GoogleOAuthClient:
        return GoogleOAuthClient(
            CLIENT_ID,
            "test-client-secret",
            f"{PUBLIC_URL}/auth/google/callback",
            DOMAIN,
            http=httpx.Client(transport=httpx.MockTransport(self.token_endpoint)),
            signing_key=lambda _token: self.private_key.public_key(),
        )


@dataclass
class Harness:
    """A service and everything behind it, for one test."""

    service: AuthService
    store: SqliteAuthStore
    clock: FakeClock
    email: RecordingEmailSender
    google: FakeGoogle
    config: AuthConfig
    db_path: Path

    def sign_in_by_email(self, address: str = STAFF) -> SignInResult:
        self.service.request_email_code(address)
        result = self.service.finish_email_code(email=address, code=self.email.last_code)
        self.clock.advance(seconds=31)  # past the resend interval, ready for the next code
        return result

    def sign_in_with_google(self, next_path: str | None = None) -> SignInResult:
        start = self.service.start_google(next_path)
        state = self.google.browser_visits(start.authorization_url)
        return self.service.finish_google(code="good-code", state=state, flow=start.flow)


def make_harness(
    tmp_path: Path,
    *,
    with_google: bool = True,
    with_email: bool = True,
    bootstrap_admins: frozenset[str] = frozenset({ADMIN}),
) -> Harness:
    clock = FakeClock()
    config = AuthConfig(
        secret=SECRET,
        allowed_domain=DOMAIN,
        environment="development",
        public_url=PUBLIC_URL,
        bootstrap_admins=bootstrap_admins,
    )
    db_path = tmp_path / "auth.sqlite"
    store = SqliteAuthStore(db_path)
    email = RecordingEmailSender()
    google = FakeGoogle()
    service = AuthService(
        config,
        store,
        tokens=TokenService(config, store.refresh_tokens, clock),
        email_codes=EmailCodeService(
            config, store.email_challenges, email if with_email else None, clock
        ),
        google=google.client() if with_google else None,
        clock=clock,
    )
    return Harness(service, store, clock, email, google, config, db_path)
