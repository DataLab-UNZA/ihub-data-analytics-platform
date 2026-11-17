# ADR-013: One unit scope for the Organisation counts and the publication list

- **Status:** Proposed
- **Date:** November 17, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

The Organisation screen counts publications per school ([ADR-012](ADR-012-school-output-from-the-staff-roster.md) with the staff roster, [ADR-004](ADR-004-research-mart-organisations-and-authorships.md) without it). Its "View publications" link opened the publication list for the whole university, and the Unit filter in the top bar was never sent to the API, so "Explore 2,186 publications" appeared where a school's own count (for example 1,388) was expected.

## Decision

1. **A unit is a set of publication keys, decided in one place.** `ihub.api.units.UnitScope` returns the publications of every unit for a period: roster-linked publications per school when a roster exists, department-based ones otherwise, plus "Not credited to a school" (the rest of the corpus) in roster mode. The Organisation counts, the Unit filter options and the list all read this one result, so they cannot disagree.
2. **The shared filter carries the scope.** `PublicationFilter` has `publication_keys`. The list, the count, the CSV export and the new type and source breakdown (`/api/publications-breakdown`) all build their WHERE clause from it. Routes take a `unit` parameter; an unknown unit is a 400. A unit with no publications matches nothing (it never falls back to everything).
3. **Source counts per unit** come from `marts.bridge_publication_source` and `dim_source_system` (OpenAlex, repository, OJS, ORCID), counted over the unit's publications for the period and returned with `/api/organisation`. A source missing from the mart is shown as "–", not 0.
4. **The web app** links to `/publications?unit=<name>`. A unit in the URL wins over the Unit filter; `unit=all` shows every unit. A unit the API does not know (a stale cookie) is ignored.

## Consequences

- Without a roster the units are schools only; a department links to its school's list.
- A publication with authors in several schools is in each school's list, so school counts add up to more than the corpus.
- Resolving a unit computes the period's school sets (about 6,000 candidate authors; well under a second, cached roster links).
- Only publication keys and school-level counts leave the backend: no name, staff ID or per-person result.
- **Roster credit only reaches OpenAlex publications.** Repository and OJS authors are name-only and flagged `is_unza_author = false`, so they are never matched to the roster. A school's OpenAlex count therefore equals its total, and its repository and journal counts only cover publications that OpenAlex also holds. Repository-only and journal-only publications fall under "Not credited to a school". Crediting them needs name-only authors matched to the roster (future work); across the whole corpus the sources are not subsets of one another.
