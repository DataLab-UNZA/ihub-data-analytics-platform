"""Google sign-in: OpenID Connect authorisation-code flow with PKCE (ADR-010).

The API builds the authorisation URL, exchanges the code with the client secret, and
verifies the ID token itself: signature (Google's JWKS), ``iss``, ``aud``, ``exp``,
``nonce``, ``email_verified``, and that both the ``hd`` claim and the email domain are the
allowed UNZA domain. With the domain set to ``*`` (testing only) any verified Google
account is accepted, Gmail included. The ``hd`` request parameter only tunes Google's
account chooser; the ``hd`` claim check is what enforces the rule.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from ihub.auth.config import ANY_DOMAIN
from ihub.auth.errors import IdentityRejectedError, InvalidRequestError, UpstreamError

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
CLOCK_SKEW_SECONDS = 30

SigningKeyResolver = Callable[[str], Any]


@dataclass(frozen=True)
class GoogleIdentity:
    """A verified UNZA Google account."""

    subject: str
    email: str
    name: str | None


def _jwks_resolver() -> SigningKeyResolver:
    client = jwt.PyJWKClient(JWKS_URI, cache_keys=True)

    def resolve(token: str) -> Any:
        return client.get_signing_key_from_jwt(token).key

    return resolve


class GoogleOAuthClient:
    """Talks to Google for one OAuth client. ``http`` and ``signing_key`` are injectable."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        allowed_domain: str,
        *,
        http: httpx.Client | None = None,
        signing_key: SigningKeyResolver | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._domain = allowed_domain.lower()
        self._http = http or httpx.Client(timeout=10.0)
        self._signing_key = signing_key or _jwks_resolver()

    def authorization_url(self, *, state: str, nonce: str, code_challenge: str) -> str:
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": self._redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
            "access_type": "online",
        }
        if self._domain != ANY_DOMAIN:
            params["hd"] = self._domain
        return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    def exchange_code(self, *, code: str, code_verifier: str, nonce: str) -> GoogleIdentity:
        """Swap the authorisation code for an ID token and verify it."""
        try:
            response = self._http.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "code_verifier": code_verifier,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise UpstreamError(
                "Google did not respond. Try again.", reason="google_unreachable"
            ) from exc
        if response.status_code != 200:
            raise InvalidRequestError(
                "Google did not accept this sign-in. Start again.", reason="code_rejected"
            )
        id_token = response.json().get("id_token")
        if not isinstance(id_token, str):
            raise UpstreamError("Google sent an unexpected answer.", reason="no_id_token")
        return self.verify_id_token(id_token, nonce=nonce)

    def verify_id_token(self, id_token: str, *, nonce: str) -> GoogleIdentity:
        """Check every claim ADR-010 lists; IdentityRejectedError if any fails."""
        unverifiable = "Your Google sign-in could not be verified. Start again."
        try:
            key = self._signing_key(id_token)
        except jwt.PyJWKClientConnectionError as exc:
            raise UpstreamError("Google did not respond. Try again.", reason="jwks") from exc
        except jwt.PyJWTError as exc:
            raise IdentityRejectedError(unverifiable, reason="invalid_token") from exc
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self._client_id,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["iss", "aud", "exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise IdentityRejectedError(unverifiable, reason="invalid_token") from exc
        if claims["iss"] not in ISSUERS:
            raise IdentityRejectedError(unverifiable, reason="wrong_issuer")
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise IdentityRejectedError(unverifiable, reason="nonce_mismatch")
        if claims.get("email_verified") not in (True, "true"):
            raise IdentityRejectedError(
                "Your Google email address is not verified.", reason="unverified_email"
            )
        email = str(claims.get("email", "")).lower()
        wrong_domain = self._domain != ANY_DOMAIN and (
            claims.get("hd") != self._domain or not email.endswith(f"@{self._domain}")
        )
        if wrong_domain:
            raise IdentityRejectedError(
                f"Use your UNZA Google account (an @{self._domain} address).",
                reason="wrong_domain",
            )
        name = claims.get("name")
        return GoogleIdentity(
            subject=str(claims["sub"]), email=email, name=name if isinstance(name, str) else None
        )
