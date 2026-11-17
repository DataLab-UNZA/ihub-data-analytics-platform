"""Outgoing email behind one interface, so any mail provider can be plugged in.

- :class:`~ihub.mail.transport.MailTransport` is the interface: ``send(message)``.
- :class:`~ihub.mail.transport.SmtpTransport` works with any SMTP provider (Gmail or
  Google Workspace, Microsoft 365, Brevo, SendGrid, Mailgun, a university relay...).
- :class:`~ihub.mail.transport.ConsoleTransport` prints mail instead (development only).
- :mod:`ihub.mail.registry` picks the transport named by ``IHUB_MAIL_TRANSPORT``; a new
  provider (for example an HTTP API) is added with ``register_transport(name, factory)``.

Check delivery with ``uv run python -m ihub.mail --to you@example.org``.
"""

from ihub.mail.registry import register_transport, transport_from_settings
from ihub.mail.transport import (
    ConsoleTransport,
    MailDeliveryError,
    MailTransport,
    SmtpConfig,
    SmtpTransport,
)

__all__ = [
    "ConsoleTransport",
    "MailDeliveryError",
    "MailTransport",
    "SmtpConfig",
    "SmtpTransport",
    "register_transport",
    "transport_from_settings",
]
