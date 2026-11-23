"""Suggesting author links for staff the name matching could not connect (ADR-014).

The roster and the publication sources sometimes spell one person differently ("MUKELEBAI" in
the roster, "Mukelabai" in OpenAlex). Matching exact words cannot connect them, and a looser
automatic match would join different people with similar Zambian names. So this module only
*suggests*: it lists, for each staff member who has no linked author, the authors whose name
is a close spelling of theirs. A person reviews the list and confirms the right ones (see
:mod:`ihub.staff.overrides`); nothing here changes who is credited by itself.

A suggestion needs every word of the author's name (at least two words, a repeated name counts)
to be a close spelling of one of the staff member's words, and a word that is not spelled the
same must be long enough (:data:`MIN_FUZZY_LENGTH`) for one wrong letter to be likely a typo
rather than a different name.
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from ihub.staff.attribution import LinkResult
from ihub.staff.names import name_words
from ihub.staff.roster import Roster, StaffMember

#: How alike two words must be (0 to 1) to count as the same word spelled differently.
THRESHOLD = 0.84
#: Words shorter than this must be spelled exactly: "Mwansa" and "Mwanza" are different names.
MIN_FUZZY_LENGTH = 7
#: At most this many suggestions per staff member, best first.
PER_STAFF = 3


@dataclass(frozen=True)
class Suggestion:
    """An author whose name is a close spelling of a staff member's, to be confirmed."""

    staff_id: str
    staff_name: str
    school: str | None
    author_key: str
    author_name: str
    author_id: str  # an OpenAlex author ID or an ORCID iD, the form the overrides file takes
    score: float  # 1.0 when the words are spelled the same, less the more they differ


def _close(word: str, other: str) -> float:
    """Similarity of two words, or 0 when they are too different (or too short to be a typo)."""
    if word == other:
        return 1.0
    if min(len(word), len(other)) < MIN_FUZZY_LENGTH:
        return 0.0
    ratio = difflib.SequenceMatcher(None, word, other).ratio()
    return ratio if ratio >= THRESHOLD else 0.0


def _score(tokens: Sequence[str], member: StaffMember) -> float:
    """Mean closeness of the author's words to the staff member's, 0 if any word has no match."""
    total = 0.0
    for token in tokens:
        best = max((_close(token, word) for word in member.words), default=0.0)
        if not best:
            return 0.0
        total += best
    return total / len(tokens)


def suggest(
    roster: Roster,
    result: LinkResult,
    authors: Iterable[tuple[str, str]],
    identifiers: Mapping[str, str],
) -> list[Suggestion]:
    """Return suggestions for staff with no linked author, from authors not yet linked to anyone.

    ``authors`` are ``(author_key, author_name)`` pairs; ``identifiers`` maps an author key to
    its OpenAlex ID or ORCID iD (an author with neither cannot be pinned, so is skipped).
    """
    linked_staff = {link.staff_id for link in result.links.values() if link.staff_id}
    taken = {key for key, link in result.links.items() if link.staff_id}
    pool = []
    by_word: dict[str, list[int]] = defaultdict(list)
    for key, name in authors:
        tokens = [word for word in name_words(name) if len(word) > 1]
        if key in taken or len(tokens) < 2 or key not in identifiers:
            continue
        pool.append((key, name, tokens))
        for word in set(tokens):
            by_word[word].append(len(pool) - 1)
    vocabulary: dict[tuple[str, int], list[str]] = defaultdict(list)
    for word in by_word:
        vocabulary[(word[0], len(word))].append(word)

    suggestions: list[Suggestion] = []
    for member in roster.members:
        if member.staff_id in linked_staff or not member.words:
            continue
        found: set[int] = set()
        for word in member.words:
            for length in (len(word) - 1, len(word), len(word) + 1):
                for token in vocabulary.get((word[0], length), ()):
                    if _close(token, word):
                        found.update(by_word[token])
        scored = []
        for index in found:
            key, name, tokens = pool[index]
            score = _score(tokens, member)
            if score:
                scored.append((score, key, name))
        scored.sort(key=lambda item: (-item[0], item[2]))
        for score, key, name in scored[:PER_STAFF]:
            suggestions.append(
                Suggestion(
                    staff_id=member.staff_id,
                    staff_name=member.display_name,
                    school=member.school,
                    author_key=key,
                    author_name=name,
                    author_id=identifiers[key],
                    score=round(score, 3),
                )
            )
    suggestions.sort(key=lambda s: (s.staff_name.casefold(), -s.score))
    return suggestions
