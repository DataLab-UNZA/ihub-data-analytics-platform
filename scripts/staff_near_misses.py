"""List staff the name matching could not link, with the authors that look like them.

Run it locally, where the private roster is. Check each line with the person or with HR, and
for the ones that are right, add a row to ``staff_author_overrides.csv`` next to the roster
(see ``ihub.staff.overrides``). The output contains names from the roster: do not paste it
into an issue, a pull request or a chat.

    uv run python scripts/staff_near_misses.py
    uv run python scripts/staff_near_misses.py --db data/real.duckdb --roster path/to/roster.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ihub.mart import staff_links
from ihub.mart.research import YearRange, year_bounds
from ihub.settings import get_settings
from ihub.staff import attribution
from ihub.staff.names import name_words
from ihub.staff.roster import StaffMember


def candidates(
    member: StaffMember, authors: list[tuple[str, str, frozenset[str], list[str]]]
) -> list[tuple[str, str]]:
    """Return ``(author_key, author_name)`` for authors that look like ``member``.

    An author looks like the staff member when they share at least two words of the name, or
    when every word of the author's name is one of the staff member's words and the name has
    at least two words (a repeated given name, as in "Mukelabai Mukelabai").
    """
    found = []
    for key, name, words, tokens in authors:
        shared = words & member.words
        if len(shared) >= 2 or (len(tokens) >= 2 and words and words <= member.words):
            found.append((key, name))
    return found


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # names can hold any character, on any console
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=settings.ihub_duckdb_path)
    parser.add_argument("--roster", type=Path, default=settings.ihub_staff_roster_path)
    args = parser.parse_args(argv)
    if args.roster is None or not args.roster.is_file():
        print("No roster file found. Pass --roster.", file=sys.stderr)
        return 1

    linked = attribution.linked_authors(args.db, args.roster)
    if linked is None:
        print("Could not read the database or the roster.", file=sys.stderr)
        return 1
    roster, result = linked
    matched = {link.staff_id for link in result.links.values() if link.staff_id}
    authors = []
    for key, name in staff_links.unza_authors(args.db):
        tokens = [word for word in name_words(name) if len(word) > 1]
        authors.append((key, name, frozenset(tokens), tokens))
    ids = {
        key: (openalex, orcid) for key, openalex, orcid in staff_links.author_identifiers(args.db)
    }
    counts = dict((key, n) for key, n in _publication_counts(args.db, [a[0] for a in authors]))

    writer = csv.writer(sys.stdout)
    writer.writerow(
        ["Staff ID", "Author ID", "Staff name", "School", "Author name", "Publications"]
    )
    for member in roster.members:
        if member.school is None or member.staff_id in matched:
            continue
        for key, name in candidates(member, authors):
            openalex, orcid = ids.get(key, (None, None))
            author_id = (openalex or "").rsplit("/", 1)[-1] or orcid or ""
            writer.writerow(
                [
                    member.staff_id,
                    author_id,
                    member.display_name,
                    member.school,
                    name,
                    counts.get(key, 0),
                ]
            )
    return 0


def _publication_counts(db: Path, keys: list[str]) -> list[tuple[str, int]]:
    """Return ``(author_key, publications)`` over every year."""
    pairs = staff_links.author_publications(db, keys, YearRange(*_all_years(db)))
    totals: dict[str, int] = {}
    for author, _ in pairs:
        totals[author] = totals.get(author, 0) + 1
    return list(totals.items())


def _all_years(db: Path) -> tuple[int, int]:
    bounds = year_bounds(db)
    return bounds.start, bounds.end


if __name__ == "__main__":
    raise SystemExit(main())
