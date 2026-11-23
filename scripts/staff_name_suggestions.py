"""Write a spreadsheet of suggested author links for staff the name matching could not connect.

Run it locally, where the private roster is. It writes ``staff_name_suggestions.csv`` next to the
roster (git-ignored). Open it in a spreadsheet, check each row with the person or with HR, and
type ``yes`` in the Confirm column of the rows that are the right person. Save, and the next
request reads the confirmed rows; nothing else needs doing. Re-running keeps your earlier answers.

The file contains names from the roster: do not paste it into an issue, a pull request or a chat.

    uv run python scripts/staff_name_suggestions.py
    uv run python scripts/staff_name_suggestions.py --db data/real.duckdb --roster roster.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from ihub.mart import staff_links
from ihub.mart.research import YearRange, year_bounds
from ihub.settings import get_settings
from ihub.staff import attribution, suggestions
from ihub.staff.overrides import normalise_author_id, suggestions_path

COLUMNS = [
    "Confirm",
    "Staff ID",
    "Author ID",
    "Staff name",
    "School",
    "Author name",
    "Publications",
    "Match",
]


def read_answered(path: Path) -> list[dict[str, str]]:
    """Return the rows of ``path`` that a person has answered (anything in Confirm).

    A confirmed row is what makes the link count, so it must survive a re-run even though the
    staff member no longer needs a suggestion; an answered "no" is kept so it is not asked again.
    """
    if not path.is_file():
        return []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("Confirm") or "").strip()]


def main(argv: list[str] | None = None) -> int:
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

    authors = staff_links.unza_authors(args.db)
    identifiers = {}
    for key, openalex, orcid in staff_links.author_identifiers(args.db):
        found = normalise_author_id(openalex) or normalise_author_id(orcid)
        if found:
            identifiers[key] = found
    found = suggestions.suggest(roster, result, authors, identifiers)

    bounds = year_bounds(args.db)
    pairs = staff_links.author_publications(
        args.db, [s.author_key for s in found], YearRange(bounds.start, bounds.end)
    )
    counts = Counter(author for author, _ in pairs)

    target = suggestions_path(args.roster)
    answered = read_answered(target)
    done = {(row.get("Staff ID", "").strip(), row.get("Author ID", "").strip()) for row in answered}
    rows = [{column: row.get(column, "") for column in COLUMNS} for row in answered]
    for s in found:
        if (s.staff_id, s.author_id) in done:
            continue
        match = "same spelling" if s.score == 1.0 else f"close spelling ({s.score:.0%})"
        rows.append(
            {
                "Confirm": "",
                "Staff ID": s.staff_id,
                "Author ID": s.author_id,
                "Staff name": s.staff_name,
                "School": s.school or "Staff development fellow",
                "Author name": s.author_name,
                "Publications": str(counts.get(s.author_key, 0)),
                "Match": match,
            }
        )
    rows.sort(key=lambda row: (row["Staff name"].casefold(), row["Author name"].casefold()))
    with open(target, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    staff = len({row["Staff ID"] for row in rows})
    print(f"Wrote {len(rows)} suggestions for {staff} staff to {target}")
    print("Type yes in the Confirm column for the right person, save, and refresh the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
