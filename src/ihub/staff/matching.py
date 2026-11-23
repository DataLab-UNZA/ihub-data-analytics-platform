"""Matching one author's name to roster entries (ADR-012).

Rules, strongest first:

* ``exact``: the author's whole words are exactly the roster entry's words;
* ``author_subset``: the author leaves out a name the roster has ("Chanda Banda" for
  "BANDA CHANDA JOHN");
* ``roster_subset``: the author adds a name the roster lacks (a middle name), keeping at least
  two of the roster's words;
* ``initial``: one whole word (the surname) plus initials that fit the roster entry.

Every rule needs a word that is the roster entry's surname, and an initial that the roster entry
cannot account for rejects the match. When an author fits several roster entries the strongest
rule wins; ``initial`` matches are only accepted if exactly one entry fits.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from ihub.staff.names import PersonName
from ihub.staff.roster import StaffMember

EXACT = "exact"
AUTHOR_SUBSET = "author_subset"
ROSTER_SUBSET = "roster_subset"
INITIAL = "initial"

#: Strength of each rule (higher is stronger).
STRENGTH = {EXACT: 100, AUTHOR_SUBSET: 90, ROSTER_SUBSET: 85, INITIAL: 60}


@dataclass(frozen=True)
class Candidate:
    """A roster entry that fits an author's name, and the rule that says so."""

    member: StaffMember
    rule: str


class RosterIndex:
    """Roster entries indexed by the words of their names, for fast candidate lookup."""

    def __init__(self, members: Iterable[StaffMember]) -> None:
        self._by_word: dict[str, list[StaffMember]] = defaultdict(list)
        for member in members:
            for word in member.words:
                self._by_word[word].append(member)

    def candidates_for(self, name: PersonName) -> list[StaffMember]:
        """Roster entries sharing at least one whole word with ``name``."""
        seen: dict[int, StaffMember] = {}
        for word in name.words:
            for member in self._by_word.get(word, ()):
                seen[id(member)] = member
        return list(seen.values())


def rule_for(name: PersonName, member: StaffMember) -> str | None:
    """Return the rule by which ``name`` fits ``member``, or None if it does not."""
    words = name.words
    if not words or not (words & member.surname):
        return None  # a match must contain a surname that is on the roster
    unexplained_initials = name.initials - member.initials
    if len(words) >= 2:
        if words == member.words:
            return EXACT
        if unexplained_initials:
            return None
        if words <= member.words:
            return AUTHOR_SUBSET
        if member.words <= words and len(member.words) >= 2:
            return ROSTER_SUBSET
        return None
    if name.initials and not unexplained_initials:
        return INITIAL
    return None


@dataclass(frozen=True)
class MatchOutcome:
    """The result of matching one name: the fitting entries, or that the name was ambiguous."""

    candidates: tuple[Candidate, ...] = ()
    ambiguous: bool = False  # an initial fits several entries, so none is chosen


def match_name(name: PersonName, index: RosterIndex) -> MatchOutcome:
    """Return the strongest-fitting roster entries for ``name``.

    All returned candidates share the same rule. An ``initial`` rule is ambiguous unless exactly
    one entry fits, because "L. Tembo" is not enough to choose between several Tembos.
    """
    fits = [
        Candidate(member, rule)
        for member in index.candidates_for(name)
        if (rule := rule_for(name, member)) is not None
    ]
    if not fits:
        return MatchOutcome()
    best = max(STRENGTH[c.rule] for c in fits)
    top = tuple(c for c in fits if STRENGTH[c.rule] == best)
    if top[0].rule == INITIAL and len(top) > 1:
        return MatchOutcome(ambiguous=True)
    return MatchOutcome(top)
