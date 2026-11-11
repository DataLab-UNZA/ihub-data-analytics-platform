"""Certificate checking for sources whose servers send an incomplete certificate chain.

Some servers (journals.unza.zm, for one) send only their own certificate and leave out the
intermediate one. Browsers fetch the missing certificate themselves; Python does not, so
the connection fails. Instead of turning checking off, a source lists the missing public
intermediate certificates in ``config/sources.yml`` (``ca_certificates``), and they are
added to the standard CA bundle:

- :func:`ca_bundle` gives a bundle file path, for ``requests`` (and so Sickle);
- :func:`ssl_context` gives an :class:`ssl.SSLContext`, for ``httpx``.

With no extra certificates both return the defaults, so nothing changes for other sources.
"""

from __future__ import annotations

import hashlib
import ssl
import tempfile
from collections.abc import Sequence
from pathlib import Path

import certifi

PEM_MARKER = "-----BEGIN CERTIFICATE-----"


def _read_certificates(paths: Sequence[str | Path]) -> str:
    """Return the PEM text of every file in ``paths``, checking that each holds a certificate."""
    texts = []
    for path in paths:
        file = Path(path)
        if not file.is_file():
            raise ValueError(f"CA certificate file not found: {file}")
        text = file.read_text(encoding="ascii")
        if PEM_MARKER not in text:
            raise ValueError(f"{file} does not hold a PEM certificate")
        texts.append(text)
    return "\n".join(texts)


def ca_bundle(extra: Sequence[str | Path] | None) -> str | bool:
    """Return ``True`` (the default bundle) or the path of the default bundle plus ``extra``.

    The combined file is written once to the temporary directory, named after a hash of its
    contents, so repeated runs reuse it and a changed certificate gives a new file.
    """
    if not extra:
        return True
    combined = Path(certifi.where()).read_text(encoding="ascii") + "\n" + _read_certificates(extra)
    digest = hashlib.sha256(combined.encode("ascii")).hexdigest()[:16]
    bundle = Path(tempfile.gettempdir()) / f"ihub-ca-bundle-{digest}.pem"
    if not bundle.is_file():
        partial = bundle.with_suffix(".tmp")
        partial.write_text(combined, encoding="ascii")
        partial.replace(bundle)
    return str(bundle)


def ssl_context(extra: Sequence[str | Path] | None) -> ssl.SSLContext:
    """Return a verifying SSL context that trusts the default bundle plus ``extra``."""
    context = ssl.create_default_context(cafile=certifi.where())
    if extra:
        context.load_verify_locations(cadata=_read_certificates(extra))
    return context
