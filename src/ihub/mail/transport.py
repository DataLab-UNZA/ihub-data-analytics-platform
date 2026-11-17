"""The mail transport interface and the built-in transports.

A transport delivers a finished :class:`email.message.EmailMessage`. It knows nothing
about sign-in codes or any other feature, so features compose messages and any transport
can deliver them.
"""

from __future__ import annotations

import smtplib
import ssl
import sys
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol


class MailDeliveryError(Exception):
    """The message could not be delivered. The text never contains credentials."""


class MailTransport(Protocol):
    """Delivers one email. Implement ``send`` to plug in a new provider."""

    def send(self, message: EmailMessage) -> None:
        """Deliver ``message`` or raise MailDeliveryError."""
        ...


@dataclass(frozen=True)
class SmtpConfig:
    """How to reach an SMTP server. Port 587 uses STARTTLS; 465 needs ``use_ssl=True``."""

    host: str
    port: int = 587
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    use_ssl: bool = False
    timeout: float = 15.0


class SmtpTransport:
    """Sends through any SMTP server, always over TLS (STARTTLS or implicit TLS)."""

    def __init__(self, config: SmtpConfig, *, smtp_module: object = smtplib) -> None:
        self._config = config
        self._smtp = smtp_module  # replaceable in tests

    def send(self, message: EmailMessage) -> None:
        config = self._config
        context = ssl.create_default_context()
        try:
            if config.use_ssl:
                client = self._smtp.SMTP_SSL(  # type: ignore[attr-defined]
                    config.host, config.port, timeout=config.timeout, context=context
                )
            else:
                client = self._smtp.SMTP(  # type: ignore[attr-defined]
                    config.host, config.port, timeout=config.timeout
                )
            with client:
                if not config.use_ssl:
                    client.starttls(context=context)
                if config.username:
                    client.login(config.username, config.password or "")
                client.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise MailDeliveryError(
                f"The SMTP server {config.host} refused the username or password "
                f"(code {exc.smtp_code})."
            ) from exc
        except smtplib.SMTPException as exc:
            raise MailDeliveryError(
                f"The SMTP server {config.host} refused the message: {type(exc).__name__}."
            ) from exc
        except OSError as exc:
            raise MailDeliveryError(
                f"Could not connect to {config.host}:{config.port} ({type(exc).__name__})."
            ) from exc


class ConsoleTransport:
    """Development only: prints each message to standard error instead of sending it."""

    def __init__(self, stream: object = None) -> None:
        self._stream = stream

    def send(self, message: EmailMessage) -> None:
        stream = self._stream or sys.stderr
        body = message.get_body(preferencelist=("plain",))
        text = body.get_content() if body is not None else ""
        print(
            f"[ihub mail, not sent] To: {message['To']} | Subject: {message['Subject']}\n{text}",
            file=stream,  # type: ignore[arg-type]
            flush=True,
        )
