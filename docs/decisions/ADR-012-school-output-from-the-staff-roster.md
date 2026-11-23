# ADR-012: Credit publications to schools by matching authors to the staff roster

- **Status:** Proposed
- **Date:** November 17, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

The Organisation screen counted publications per school from department evidence only: affiliation text, ORCID employments and repository collection names ([ADR-003](ADR-003-staging-and-department-attribution.md), [ADR-004](ADR-004-research-mart-organisations-and-authorships.md)). Most publications ended up under "Unassigned department" (about 17,700 of 24,500), so the school totals said little.

UNZA's HR office provided a staff roster (surname, first name, second name, title, occupation, school; 854 rows). [ADR-009](ADR-009-user-store-and-staff-data.md) already allows the roster to supply school membership and headcounts per school, and says it must be private. This ADR records how the roster is used to credit schools, and what stays private.

## Decision

1. **The roster is private and stays out of the repository.** It lives in `data/private/staff_roster.csv` (git-ignored through `data/*`), at the path in `IHUB_STAFF_ROSTER_PATH`. It is never added to `ihub.duckdb`, a release asset, a log or a test. Tests use invented names.
2. **Authors are matched to the roster by name**, in `ihub.staff`. Only authors the mart already flags as UNZA authors (`dim_author.is_unza_author`) are considered. Names are compared as sets of normalised words, so "Chanda Banda", "Banda, Chanda" and "BANDA CHANDA JOHN" are the same person. Matching tiers, strongest first:
   - **exact:** the same words;
   - **author subset:** the author leaves out a middle name;
   - **roster subset:** the author adds a middle name;
   - **initial:** surname plus an initial that fits the roster's given names, accepted only when one roster entry fits.
   A name must include a surname that is on the roster, and an initial that the roster entry does not have rejects the match.
3. **A publication counts once in every school with a matched author** ("each school gets credit"), so school totals add up to more than the number of publications.
4. **Ambiguous names are not guessed.** When one name fits several staff members in different schools, the author's existing department evidence (`org_basis = author_department`) decides if it names exactly one of the candidate schools. Otherwise the author gets no credit.
5. **"SDF" is not a school.** Staff development fellows have no school in the roster. A fellow who matches uses their department evidence, if any. Other roster labels that are not in the school list (INESOR, DRGS) are kept as their own units. The mapping from roster labels to school names is in `ihub.staff.roster`.
6. **Authors outside the roster keep their department-based credit**, reported separately ("including department evidence"), so the effect of the roster stays visible.
7. **Only school-level numbers leave the backend.** The API returns, per school, publication counts and the number of matched authors, and overall match statistics. It never returns a name, a staff ID or a per-person result.
8. **Without a roster the screen falls back** to the department-based counts, so environments that do not have the file (such as production today) are unchanged.

## Consequences

- The roster is not in the Docker image, so production keeps the department-based counts until the private store from ADR-009 exists and the roster is loaded there. Until UNZA confirms its obligations under Zambia's Data Protection Act, 2021 (see ADR-009), the real roster is used only on a developer's machine.
- The roster has 854 people, a fraction of UNZA's academic staff, and it is a snapshot. Retired or departed authors, and anyone not listed, get no roster credit.
- A name match is not proof of identity. Common names can match the wrong person; ambiguous cases are left uncredited, and the match statistics are shown on the screen.
- Roster schools follow HR's structure, which differs from the department-based one (nursing and public health staff are filed under Medicine). The roster wins, as decided.
- The results are computed when asked and kept in memory until the database or roster file changes. At this size (about 6,000 candidate authors) it takes well under a second.

## Alternatives considered

- **Add the roster to the pipeline and the mart.** Rejected: the mart is published publicly.
- **Match only on ORCID.** The roster has no ORCID, and many authors have none.
- **Fuzzy (edit-distance) matching.** Catches spelling variants but multiplies false matches between common Zambian names. Word-set matching is easier to explain and check.
- **Let an admin confirm every match.** The right control for a production roster (ADR-009); too slow for the first version.
