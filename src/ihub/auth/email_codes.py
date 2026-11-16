"""Email one-time sign-in codes (ADR-010).

A six-digit code from :mod:`secrets` is sent to the address and stored only as an HMAC
under a server-side key, bound to its challenge. A code is valid for 10 minutes, used once,
and allows 5 wrong attempts; asking again replaces it. Requests are limited per address:
one every 30 seconds and five an hour.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import smtplib
import ssl
import sys
import uuid
from dataclasses import replace
from datetime import timedelta
from email.message import EmailMessage
from typing import Protocol

from ihub.auth.config import AuthConfig, Clock
from ihub.auth.errors import (
    InvalidCodeError,
    MethodUnavailableError,
    RateLimitedError,
    UpstreamError,
)
from ihub.auth.models import EmailChallenge
from ihub.auth.store import EmailChallengeRepository

CODE_DIGITS = 6
_HOUR = timedelta(hours=1)


class EmailSender(Protocol):
    """Delivers a sign-in code. Implementations must never log the code in production."""

    def send_sign_in_code(self, to: str, code: str, valid_minutes: int) -> None: ...


def sign_in_message(to: str, sender: str, code: str, valid_minutes: int) -> EmailMessage:
    """The plain-text email that carries a sign-in code."""
    message = EmailMessage()
    message["Subject"] = "Your iHub sign-in code"
    message["From"] = sender
    message["To"] = to
    message.set_content(
        "Your iHub Analytics sign-in code is:\n\n"
        f"    {code}\n\n"
        f"It expires in {valid_minutes} minutes and can be used once.\n"
        "If you did not try to sign in, you can ignore this email.\n\n"
        "iHub Analytics, University of Zambia\n"
    )
    return message


class ConsoleEmailSender:
    """Development only: prints the code to the API's console instead of sending it."""

    def send_sign_in_code(self, to: str, code: str, valid_minutes: int) -> None:
        print(
            f"[ihub dev] Sign-in code for {to}: {code} (valid for {valid_minutes} minutes)",
            file=sys.stderr,
            flush=True,
        )


class SmtpEmailSender:
    """Sends codes through any SMTP mailbox: STARTTLS on 587, or implicit TLS on 465."""

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        *,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = False,
        timeout: float = 15.0,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._timeout = timeout

    def send_sign_in_code(self, to: str, code: str, valid_minutes: int) -> None:
        message = sign_in_message(to, self._sender, code, valid_minutes)
        context = ssl.create_default_context()
        try:
            if self._use_ssl:
                smtp: smtplib.SMTP = smtplib.SMTP_SSL(
                    self._host, self._port, timeout=self._timeout, context=context
                )
            else:
                smtp = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
            with smtp:
                if not self._use_ssl:
                    smtp.starttls(context=context)
                if self._username:
                    smtp.login(self._username, self._password or "")
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise UpstreamError(
                "We could not send the email. Try again shortly.", reason="smtp_failed"
            ) from exc


class EmailCodeService:
    """Creates, sends and checks one-time codes for addresses already known to be allowed."""

    def __init__(
        self,
        config: AuthConfig,
        challenges: EmailChallengeRepository,
        sender: EmailSender | None,
        clock: Clock,
    ) -> None:
        self._config = config
        self._challenges = challenges
        self._sender = sender
        self._clock = clock
        self._key = config.key("email-code")

    @property
    def available(self) -> bool:
        return self._sender is not None

    @property
    def code_ttl_seconds(self) -> int:
        return int(self._config.email_code_ttl.total_seconds())

    @property
    def resend_after_seconds(self) -> int:
        return int(self._config.email_resend_interval.total_seconds())

    def send_code(self, email: str) -> EmailChallenge:
        """Create a challenge for ``email`` and send its code; the code is not returned."""
        if self._sender is None:
            raise MethodUnavailableError("Sign-in by email code is not available yet.")
        self._check_rate(email)
        now = self._clock()
        challenge_id = uuid.uuid4().hex
        code = f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"
        challenge = EmailChallenge(
            challenge_id=challenge_id,
            email=email,
            code_hash=self._hash(challenge_id, email, code),
            created_at=now,
            expires_at=now + self._config.email_code_ttl,
        )
        self._challenges.add(challenge)
        self._sender.send_sign_in_code(email, code, self.code_ttl_seconds // 60)
        return challenge

    def check_code(self, email: str, code: str) -> None:
        """Accept the live code for ``email`` once; InvalidCodeError otherwise."""
        now = self._clock()
        challenge = self._challenges.latest(email)
        if challenge is None or challenge.consumed_at is not None or now >= challenge.expires_at:
            raise InvalidCodeError(
                "This code has expired or was already used. Ask for a new code.",
                reason="expired_code",
            )
        limit = self._config.email_code_max_attempts
        if challenge.attempts >= limit:
            raise InvalidCodeError(
                "Too many wrong attempts. Ask for a new code.", reason="too_many_attempts"
            )
        cleaned = "".join(code.split())
        matches = (
            len(cleaned) == CODE_DIGITS
            and cleaned.isdigit()
            and hmac.compare_digest(
                self._hash(challenge.challenge_id, email, cleaned), challenge.code_hash
            )
        )
        if not matches:
            attempts = challenge.attempts + 1
            self._challenges.update(replace(challenge, attempts=attempts))
            left = limit - attempts
            plural = "s" if left != 1 else ""
            hint = f"{left} attempt{plural} left." if left else "Ask for a new code."
            raise InvalidCodeError(f"That code is not right. {hint}", reason="wrong_code")
        self._challenges.update(replace(challenge, consumed_at=now))

    def _check_rate(self, email: str) -> None:
        now = self._clock()
        latest = self._challenges.latest(email)
        interval = self._config.email_resend_interval
        if latest is not None and now - latest.created_at < interval:
            wait = math.ceil((interval - (now - latest.created_at)).total_seconds())
            raise RateLimitedError(f"Wait {wait} seconds before asking for another code.", wait)
        recent = self._challenges.created_since(email, now - _HOUR)
        if len(recent) >= self._config.email_max_per_hour:
            wait = math.ceil((recent[0] + _HOUR - now).total_seconds())
            raise RateLimitedError(
                "Too many codes were requested for this address. Try again later.", wait
            )

    def _hash(self, challenge_id: str, email: str, code: str) -> str:
        message = f"{challenge_id}:{email}:{code}".encode()
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()
