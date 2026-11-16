"""Picks the mail transport from settings; the plug-in point for new providers.

``IHUB_MAIL_TRANSPORT`` names the transport. When it is empty: ``smtp`` if
``IHUB_SMTP_HOST`` is set, otherwise ``console`` in development and none in production.

To add a provider, write a class with ``send(message)`` and register a factory::

    register_transport("sendgrid", lambda settings: SendGridTransport(api_key=...))

then set ``IHUB_MAIL_TRANSPORT=sendgrid``. Nothing else changes.
"""

from __future__ import annotations

from collections.abc import Callable

from ihub.mail.transport import ConsoleTransport, MailTransport, SmtpConfig, SmtpTransport
from ihub.settings import Settings

TransportFactory = Callable[[Settings], MailTransport]


class MailNotConfiguredError(Exception):
    """The chosen transport is unknown, incomplete, or not allowed here."""


def _smtp(settings: Settings) -> MailTransport:
    if not settings.ihub_smtp_host:
        raise MailNotConfiguredError("IHUB_SMTP_HOST is not set.")
    password = settings.ihub_smtp_password
    return SmtpTransport(
        SmtpConfig(
            host=settings.ihub_smtp_host,
            port=settings.ihub_smtp_port,
            username=settings.ihub_smtp_username or None,
            password=password.get_secret_value() if password else None,
            use_ssl=settings.ihub_smtp_ssl,
        )
    )


def _console(settings: Settings) -> MailTransport:
    if not is_development(settings):
        raise MailNotConfiguredError(
            "IHUB_MAIL_TRANSPORT=console prints messages and only works with IHUB_ENV=development."
        )
    return ConsoleTransport()


_REGISTRY: dict[str, TransportFactory] = {"smtp": _smtp, "console": _console}


def is_development(settings: Settings) -> bool:
    return settings.ihub_env.strip().lower() == "development"


def register_transport(name: str, factory: TransportFactory) -> None:
    """Make a transport selectable as ``IHUB_MAIL_TRANSPORT=<name>``."""
    _REGISTRY[name.strip().lower()] = factory


def available_transports() -> list[str]:
    return sorted(_REGISTRY)


def transport_name(settings: Settings) -> str | None:
    """The transport the settings select, or None when no mail can be sent."""
    chosen = (settings.ihub_mail_transport or "").strip().lower()
    if chosen:
        return chosen
    if settings.ihub_smtp_host:
        return "smtp"
    return "console" if is_development(settings) else None


def transport_from_settings(settings: Settings) -> MailTransport | None:
    """Build the selected transport; None when mail is not set up (production default)."""
    name = transport_name(settings)
    if name is None:
        return None
    factory = _REGISTRY.get(name)
    if factory is None:
        raise MailNotConfiguredError(
            f"Unknown IHUB_MAIL_TRANSPORT '{name}'. Available: {', '.join(available_transports())}."
        )
    return factory(settings)
