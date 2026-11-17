"""Builds the authentication service from settings, refusing unsafe set-ups (ADR-010).

- ``IHUB_ALLOWED_EMAIL_DOMAIN=*`` accepts any address, for testing; development only.
- ``IHUB_ENV`` defaults to production. Only ``development`` allows a temporary secret
  (sign-ins end when the API restarts) and the console email sender.
- Production needs a persistent user store (Firestore, ADR-009). Until it exists,
  authentication refuses to run there, because Cloud Run's disk is temporary.
- A sign-in method is offered only when it is configured: Google needs the client ID,
  client secret and public URL; email codes need a mail transport (ihub.mail).
"""

from __future__ import annotations

import logging
import secrets

from ihub.auth.config import (
    ANY_DOMAIN,
    MIN_SECRET_BYTES,
    AuthConfig,
    Clock,
    parse_email_list,
    utc_now,
)
from ihub.auth.email_codes import EmailCodeService, EmailSender, MailCodeSender
from ihub.auth.errors import AuthNotConfiguredError
from ihub.auth.google import GoogleOAuthClient
from ihub.auth.service import AuthService
from ihub.auth.sqlite_store import SqliteAuthStore
from ihub.auth.tokens import TokenService
from ihub.mail.registry import MailNotConfiguredError, transport_from_settings
from ihub.settings import Settings

logger = logging.getLogger(__name__)


def _secret(settings: Settings, development: bool) -> bytes:
    if settings.ihub_auth_secret is not None:
        secret = settings.ihub_auth_secret.get_secret_value().encode()
        if len(secret) < MIN_SECRET_BYTES:
            raise AuthNotConfiguredError(
                f"Sign-in is not available: IHUB_AUTH_SECRET must be at least "
                f"{MIN_SECRET_BYTES} characters."
            )
        return secret
    if development:
        logger.warning(
            "IHUB_AUTH_SECRET is not set: using a temporary secret. "
            "Everyone is signed out when the API restarts."
        )
        return secrets.token_bytes(MIN_SECRET_BYTES)
    raise AuthNotConfiguredError("Sign-in is not available: IHUB_AUTH_SECRET is not set.")


def _email_sender(settings: Settings) -> EmailSender | None:
    """Codes go through the configured mail transport (ihub.mail); None if there is none."""
    try:
        transport = transport_from_settings(settings)
    except MailNotConfiguredError as exc:
        raise AuthNotConfiguredError(f"Email sign-in is not available: {exc}") from exc
    if transport is None:
        return None
    sender = settings.ihub_smtp_from or settings.ihub_smtp_username or "ihub@localhost"
    return MailCodeSender(transport, sender)


def _google(settings: Settings, config: AuthConfig) -> GoogleOAuthClient | None:
    secret = settings.ihub_google_client_secret
    redirect_uri = config.google_redirect_uri
    if not (settings.ihub_google_client_id and secret and redirect_uri):
        return None
    return GoogleOAuthClient(
        settings.ihub_google_client_id,
        secret.get_secret_value(),
        redirect_uri,
        config.allowed_domain,
    )


def build_auth_service(settings: Settings, *, clock: Clock = utc_now) -> AuthService:
    """The configured service, or AuthNotConfiguredError explaining what is missing."""
    environment = settings.ihub_env.strip().lower()
    development = environment == "development"
    secret = _secret(settings, development)
    if settings.ihub_allowed_email_domain.strip() == ANY_DOMAIN:
        if not development:
            raise AuthNotConfiguredError(
                "Sign-in is not available: IHUB_ALLOWED_EMAIL_DOMAIN=* (any address) is for "
                "testing and only works with IHUB_ENV=development."
            )
        logger.warning("IHUB_ALLOWED_EMAIL_DOMAIN=*: any email address can sign in (testing).")
    config = AuthConfig(
        secret=secret,
        allowed_domain=settings.ihub_allowed_email_domain,
        environment=environment,
        public_url=settings.ihub_public_url,
        bootstrap_admins=parse_email_list(settings.ihub_bootstrap_admins),
    )
    if not development and not settings.ihub_allow_ephemeral_auth:
        raise AuthNotConfiguredError(
            "Sign-in is not available: production needs a persistent user store, or set "
            "IHUB_ALLOW_EPHEMERAL_AUTH=true to use the Cloud Run instance's temporary disk."
        )
    store = SqliteAuthStore(settings.ihub_auth_db_path)
    return AuthService(
        config,
        store,
        tokens=TokenService(config, store.refresh_tokens, clock),
        email_codes=EmailCodeService(
            config, store.email_challenges, _email_sender(settings), clock
        ),
        google=_google(settings, config),
        clock=clock,
    )
