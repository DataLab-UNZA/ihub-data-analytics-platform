"""Rules for what users may put in their own profile: name, phone and photo.

The photo's type is read from its first bytes, never from the browser's label, so a file
that only claims to be an image is refused.
"""

from __future__ import annotations

import re

from ihub.auth.errors import InvalidRequestError

MAX_NAME_LENGTH = 100
MAX_AVATAR_BYTES = 2 * 1024 * 1024
_PHONE_CHARS = re.compile(r"^\+?[0-9 ()\-]+$")


def clean_name(value: str | None) -> str | None:
    """Trimmed display name, or None for empty."""
    if value is None:
        return None
    name = " ".join(value.split())
    if len(name) > MAX_NAME_LENGTH:
        raise InvalidRequestError(
            f"Your name can have at most {MAX_NAME_LENGTH} characters.", reason="name_too_long"
        )
    return name or None


def clean_phone(value: str | None) -> str | None:
    """A phone number with 7 to 15 digits (international format allowed), or None for empty."""
    if value is None:
        return None
    phone = " ".join(value.split())
    if not phone:
        return None
    digits = sum(char.isdigit() for char in phone)
    if not _PHONE_CHARS.match(phone) or not 7 <= digits <= 15:
        raise InvalidRequestError(
            "Enter a phone number with 7 to 15 digits, for example +260 97 123 4567.",
            reason="bad_phone",
        )
    return phone


def image_type(data: bytes) -> str:
    """The media type of a PNG, JPEG or WebP image; InvalidRequestError for anything else."""
    if len(data) > MAX_AVATAR_BYTES:
        raise InvalidRequestError("The photo must be 2 MB or smaller.", reason="photo_too_large")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise InvalidRequestError("Upload a PNG, JPEG or WebP image.", reason="photo_type")
