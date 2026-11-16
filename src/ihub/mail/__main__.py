"""Send a test email to check that mail arrives.

    uv run python -m ihub.mail --to you@example.org

Reads the same settings as the API (.env). Prints which transport and server it used,
never the username or password.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from email.message import EmailMessage

from ihub.mail.registry import MailNotConfiguredError, transport_from_settings, transport_name
from ihub.mail.transport import MailDeliveryError
from ihub.settings import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a test email with the iHub mail settings.")
    parser.add_argument("--to", required=True, help="address to send the test email to")
    args = parser.parse_args(argv)

    settings = get_settings()
    name = transport_name(settings)
    try:
        transport = transport_from_settings(settings)
    except MailNotConfiguredError as exc:
        print(f"Mail is not configured: {exc}", file=sys.stderr)
        return 2
    if transport is None:
        print(
            "Mail is not configured: set IHUB_SMTP_HOST (or IHUB_MAIL_TRANSPORT).", file=sys.stderr
        )
        return 2
    sender = settings.ihub_smtp_from or settings.ihub_smtp_username
    if not sender:
        print("Set IHUB_SMTP_FROM to the address mail is sent from.", file=sys.stderr)
        return 2

    message = EmailMessage()
    message["Subject"] = "iHub mail test"
    message["From"] = sender
    message["To"] = args.to
    message.set_content(
        "This is a test from the iHub Analytics platform.\n"
        f"Sent {datetime.now(UTC):%Y-%m-%d %H:%M} UTC with the '{name}' transport.\n"
        "If you can read this, sign-in codes can be delivered.\n"
    )
    server = f"{settings.ihub_smtp_host}:{settings.ihub_smtp_port}" if name == "smtp" else name
    try:
        transport.send(message)
    except MailDeliveryError as exc:
        print(f"Not sent: {exc}", file=sys.stderr)
        return 1
    print(f"Sent a test email to {args.to} through {server} (transport: {name}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
