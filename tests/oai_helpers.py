"""Helpers for tests that replay recorded OAI-PMH replies (never the live endpoint)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import responses

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")


def oai_replies(
    rsps: responses.RequestsMock, endpoint: str, replies: dict[tuple[str, str], str | int]
) -> None:
    """Answer GETs to ``endpoint`` from ``replies``.

    Keys are ``(verb, argument)``: the argument is the ``resumptionToken`` if one is sent,
    otherwise the ``set`` (or ``""``). Values are an XML body or an HTTP status code. Any
    other request fails the test with HTTP 599, so an unexpected call cannot pass unnoticed.
    """

    def callback(request):  # type: ignore[no-untyped-def]
        query = parse_qs(urlsplit(request.url).query)
        verb = query.get("verb", [""])[0]
        argument = query.get("resumptionToken", query.get("set", [""]))[0]
        reply = replies.get((verb, argument))
        if reply is None:
            return 599, {}, f"unexpected request {verb} {argument}"
        if isinstance(reply, int):
            return reply, {}, ""
        return 200, {"Content-Type": "text/xml; charset=utf-8"}, reply

    rsps.add_callback(responses.GET, endpoint, callback=callback)
