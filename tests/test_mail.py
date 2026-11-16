"""The mail interface (ihub.mail): SMTP transport, console transport, registry, CLI.

A fake smtplib records what the transport does; no test opens a network connection.
"""

from __future__ import annotations

import io
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pytest

from ihub.auth.email_codes import MailCodeSender
from ihub.auth.errors import UpstreamError
from ihub.auth.factory import build_auth_service
from ihub.mail import __main__ as mail_cli
from ihub.mail.registry import (
    MailNotConfiguredError,
    register_transport,
    transport_from_settings,
    transport_name,
)
from ihub.mail.transport import (
    ConsoleTransport,
    MailDeliveryError,
    SmtpConfig,
    SmtpTransport,
)
from ihub.settings import Settings


class FakeSmtp:
    """Stands in for smtplib.SMTP and smtplib.SMTP_SSL, recording every call."""

    calls: list[tuple] = []
    fail_with: Exception | None = None

    def __init__(self, host: str, port: int, **kwargs: object) -> None:
        FakeSmtp.calls.append(("connect", type(self).__name__, host, port, "context" in kwargs))
        if FakeSmtp.fail_with is not None:
            raise FakeSmtp.fail_with

    def __enter__(self) -> FakeSmtp:
        return self

    def __exit__(self, *exc: object) -> None:
        FakeSmtp.calls.append(("quit",))

    def starttls(self, context: object) -> None:
        FakeSmtp.calls.append(("starttls", context is not None))

    def login(self, user: str, password: str) -> None:
        FakeSmtp.calls.append(("login", user, bool(password)))

    def send_message(self, message: EmailMessage) -> None:
        FakeSmtp.calls.append(("send", message["To"], message["Subject"]))


class FakeSmtpSsl(FakeSmtp):
    pass


class FakeSmtpModule:
    SMTP = FakeSmtp
    SMTP_SSL = FakeSmtpSsl


@pytest.fixture(autouse=True)
def reset_fake() -> None:
    FakeSmtp.calls = []
    FakeSmtp.fail_with = None


def message(to: str = "staff@unza.ac.zm") -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = "Hello", "ihub@unza.ac.zm", to
    msg.set_content("Body text")
    return msg


def test_smtp_uses_starttls_then_logs_in_on_port_587() -> None:
    config = SmtpConfig(host="smtp.example.org", username="ihub", password="secret")
    SmtpTransport(config, smtp_module=FakeSmtpModule).send(message())
    assert FakeSmtp.calls == [
        ("connect", "FakeSmtp", "smtp.example.org", 587, False),
        ("starttls", True),
        ("login", "ihub", True),
        ("send", "staff@unza.ac.zm", "Hello"),
        ("quit",),
    ]


def test_smtp_uses_implicit_tls_on_port_465() -> None:
    config = SmtpConfig(host="smtp.example.org", port=465, use_ssl=True)
    SmtpTransport(config, smtp_module=FakeSmtpModule).send(message())
    assert FakeSmtp.calls[0] == ("connect", "FakeSmtpSsl", "smtp.example.org", 465, True)
    assert ("starttls", True) not in FakeSmtp.calls
    assert not any(call[0] == "login" for call in FakeSmtp.calls)  # no username: no login


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad credentials"), "username or password"),
        (smtplib.SMTPRecipientsRefused({}), "refused the message"),
        (ConnectionRefusedError(), "Could not connect"),
    ],
)
def test_smtp_failures_become_delivery_errors_without_secrets(
    error: Exception, expected: str
) -> None:
    FakeSmtp.fail_with = error
    config = SmtpConfig(host="smtp.example.org", username="ihub", password="hunter2")
    with pytest.raises(MailDeliveryError, match=expected) as caught:
        SmtpTransport(config, smtp_module=FakeSmtpModule).send(message())
    assert "hunter2" not in str(caught.value)


def test_the_password_is_hidden_from_repr() -> None:
    assert "hunter2" not in repr(SmtpConfig(host="h", password="hunter2"))


def test_console_transport_prints_instead_of_sending() -> None:
    out = io.StringIO()
    ConsoleTransport(out).send(message())
    assert "not sent" in out.getvalue() and "Body text" in out.getvalue()


def settings(**values: object) -> Settings:
    return Settings(_env_file=None, **values)


def test_registry_picks_smtp_when_a_host_is_set() -> None:
    assert transport_name(settings(ihub_smtp_host="smtp.example.org")) == "smtp"
    assert isinstance(
        transport_from_settings(settings(ihub_smtp_host="smtp.example.org")), SmtpTransport
    )


def test_registry_defaults_to_console_in_development_and_none_in_production() -> None:
    assert isinstance(transport_from_settings(settings(ihub_env="development")), ConsoleTransport)
    assert transport_from_settings(settings()) is None


def test_console_is_refused_in_production() -> None:
    with pytest.raises(MailNotConfiguredError, match="development"):
        transport_from_settings(settings(ihub_mail_transport="console"))


def test_unknown_transports_are_reported() -> None:
    with pytest.raises(MailNotConfiguredError, match="Available: .*smtp"):
        transport_from_settings(settings(ihub_mail_transport="carrier-pigeon"))


def test_a_new_provider_plugs_in_by_name() -> None:
    sent: list[EmailMessage] = []

    class ApiTransport:
        def send(self, message: EmailMessage) -> None:
            sent.append(message)

    register_transport("test-api", lambda _settings: ApiTransport())
    transport = transport_from_settings(settings(ihub_mail_transport="Test-API"))
    assert transport is not None
    MailCodeSender(transport, "ihub@unza.ac.zm").send_sign_in_code("a@unza.ac.zm", "123456", 10)
    assert sent[0]["To"] == "a@unza.ac.zm" and "123456" in sent[0].get_content()


def test_sign_in_codes_go_through_the_configured_transport(tmp_path: Path) -> None:
    sent: list[EmailMessage] = []

    class Recorder:
        def send(self, message: EmailMessage) -> None:
            sent.append(message)

    register_transport("recorder", lambda _settings: Recorder())
    service = build_auth_service(
        settings(
            ihub_env="development",
            ihub_mail_transport="recorder",
            ihub_smtp_from="iHub <ihub@unza.ac.zm>",
            ihub_auth_db_path=tmp_path / "auth.sqlite",
        )
    )
    service.request_email_code("staff@unza.ac.zm")
    assert sent[0]["From"] == "iHub <ihub@unza.ac.zm>"
    assert sent[0]["Subject"] == "Your iHub sign-in code"


def test_delivery_failures_reach_the_user_as_a_502() -> None:
    class Broken:
        def send(self, message: EmailMessage) -> None:
            raise MailDeliveryError("server down")

    with pytest.raises(UpstreamError) as caught:
        MailCodeSender(Broken(), "ihub@unza.ac.zm").send_sign_in_code("a@unza.ac.zm", "1", 10)
    assert caught.value.status_code == 502


def test_the_check_command_sends_a_test_email(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sent: list[EmailMessage] = []

    class Recorder:
        def send(self, message: EmailMessage) -> None:
            sent.append(message)

    register_transport("cli-recorder", lambda _settings: Recorder())
    monkeypatch.setattr(
        mail_cli,
        "get_settings",
        lambda: settings(ihub_mail_transport="cli-recorder", ihub_smtp_from="ihub@unza.ac.zm"),
    )
    assert mail_cli.main(["--to", "me@example.org"]) == 0
    assert sent[0]["To"] == "me@example.org"
    assert "Sent a test email to me@example.org" in capsys.readouterr().out
