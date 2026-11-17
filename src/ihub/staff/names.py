"""Normalising person names so the same person compares equal across spellings.

"Chanda Banda", "Banda, Chanda", "BANDA CHANDA" and "Ng'andu" / "NG'ANDU" must agree, so names
are reduced to sets of lower-case ASCII words. Word order is ignored on purpose: Zambian names
are written surname-first in some systems and surname-last in others, and a name that is the
same set of words is the same name.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

#: Honorifics that are not part of a name.
TITLES = frozenset(
    {"dr", "prof", "professor", "mr", "mrs", "ms", "miss", "eng", "rev", "hon", "mx"}
)

_APOSTROPHES = re.compile(r"[’'`´]")
_SEPARATORS = re.compile(r"[-–—_/]")
_NOT_LETTERS = re.compile(r"[^a-z\s]")


def name_words(text: str | None) -> list[str]:
    """Return the words of ``text``: lower case, no accents, apostrophes joined, hyphens split.

    Titles, digits and punctuation are dropped, so ``"Dr. Ng'andu-Banda"`` gives
    ``["ngandu", "banda"]``.
    """
    decomposed = unicodedata.normalize("NFKD", text or "")
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()
    plain = _APOSTROPHES.sub("", plain)
    plain = _SEPARATORS.sub(" ", plain)
    plain = _NOT_LETTERS.sub(" ", plain)
    return [word for word in plain.split() if word not in TITLES]


@dataclass(frozen=True)
class PersonName:
    """A name as words: whole words (two letters or more) and single-letter initials.

    ``surname_hint`` holds the words before a comma ("Banda, Chanda"), the one place a name says
    which words are the surname. It is empty for names written without a comma.
    """

    words: frozenset[str]
    initials: frozenset[str]
    surname_hint: frozenset[str] = frozenset()

    @property
    def is_empty(self) -> bool:
        return not self.words and not self.initials


def parse_person(name: str | None) -> PersonName:
    """Parse a name written either "Given Surname" or "Surname, Given"."""
    if name and "," in name:
        surname_part, _, given_part = name.partition(",")
        surname = name_words(surname_part)
        everything = surname + name_words(given_part)
        hint = frozenset(word for word in surname if len(word) > 1)
    else:
        everything = name_words(name)
        hint = frozenset()
    return PersonName(
        words=frozenset(word for word in everything if len(word) > 1),
        initials=frozenset(word for word in everything if len(word) == 1),
        surname_hint=hint,
    )
