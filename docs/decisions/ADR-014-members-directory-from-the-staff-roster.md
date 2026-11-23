# ADR-014: A Members directory of named staff, from the staff roster

- **Status:** Proposed
- **Date:** November 17, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

The Members screen was illustrative. The team asked for it to list real lecturers and researchers from the HR staff roster, with their title, unit, ORCID iD and publication count, and a profile that links to their publications.

[ADR-012](ADR-012-school-output-from-the-staff-roster.md) kept the roster private and returned school-level numbers only (decision 7). A named directory is a deliberate exception to that, so it needs its own rules. [ADR-009](ADR-009-user-store-and-staff-data.md) already allows the roster to supply titles and school membership, and requires access control and no individual rankings (`CLAUDE.md` leaves out individual staff rankings and h-index league tables).

## Decision

1. **Named staff are served only under `members:read`.** The permission is held by the unit head, executive and admin roles (`ihub.auth.rbac`). Without it the API answers 403 and the web app shows the access-restricted page. The other research routes are unchanged.
2. **What leaves the backend per person:** title, display name, school, ORCID iD (from the mart, which is public research metadata), publication counts and the person's publications. Never the staff ID, occupation or any other roster column. The URL id is an opaque hash of the staff ID.
3. **Who is listed.** A staff member appears only when a publication author's name fits exactly one roster entry in the credited school (the matching of ADR-012). Two staff with the same name in one school are not merged into one profile (the school still gets credit). Staff development fellows ("SDF" in the roster, no school) are listed too, marked as fellows: their school is the one department evidence names, if exactly one, otherwise none. A fellow with no school adds nothing to school credit. Staff with no matching author are not listed.
4. **No ranking.** The directory is always A to Z by name; there is no sort by count. All four global filters apply, through the same publication filter as the publication list: period, unit (the member's school), source and type decide which publications are counted. Only members with at least one such publication are listed, so changing a filter visibly changes who is shown.
5. **Hand-confirmed links for names the matching cannot connect.** The roster and the sources can write one person differently (for example "Kakanda, Mukelabai Alfred" and "Mukelabai Mukelabai"). A person who has checked such a case adds a row (`Staff ID`, `Author ID`: an OpenAlex author ID or an ORCID iD) to `staff_author_overrides.csv`, next to the roster and git-ignored like it. A pinned author is linked to that staff member (and credits their school) before any name matching, so a pin wins over the name; an author pinned to two people is ignored. `scripts/staff_near_misses.py` lists unmatched staff with authors that look like them, to be checked and then pinned. Its output holds names: it is for local use only.
6. **The roster stays local.** It is read from the git-ignored `data/private/staff_roster.csv`, as in ADR-012. Production has no roster, so there the directory says it needs the roster. The Data Protection Act, 2021 question in ADR-009 must be settled with UNZA before the roster is loaded into any shared environment.

## Consequences

- ADR-012 decision 7 now has this one exception, gated by `members:read`.
- A name match is not proof of identity. Common names can be matched to the wrong author, and a person can be missing when their name is written differently; the overrides file is the remedy for the second, and a wrong pin is as wrong as a wrong match, so pins are checked by a person. The profile's "Correct a record" form is not connected yet; it is shown disabled.
- Names are shown as the roster writes them, in title case (so roster typos appear as they are).
- Each request recomputes the period's totals from cached author links (about half a second for 536 members).

## Alternatives considered

- **List every roster row, including staff with no matched author.** Rejected for now: 854 rows, many with nothing to show, and it would put every name on screen rather than only those with research output.
- **Show a count-ordered list.** Rejected: it is a ranking of individuals.
- **Use the staff ID in the URL.** Rejected: it is HR data.
