# ADR-017: A public staff list as a pipeline source, so Members works in production

- **Status:** Proposed
- **Date:** November 23, 2026
- **Decided by:** Bruce Mainza, for review by Lighton Phiri

## Context

The Members directory (ADR-014) and the school credit (ADR-012) read the staff roster from the git-ignored `data/private/staff_roster.csv`. Production never has that file: `deploy.yml` copies only `ihub.duckdb` into the image, so on Cloud Run the API finds no roster and the Members screen says "The member directory needs the staff roster". Locally, with the file present, 563 staff are matched.

ADR-009, ADR-012 and ADR-014 treated the whole roster as private HR data. Most of it is not: names, titles, occupations and schools of UNZA academic staff are published on the UNZA website. The one non-public column is the **Staff ID**.

Every schema of `ihub.duckdb` is published in the public data release, including `raw_*`, `staging` and `intermediate`, not only `marts`. Anything a connector fetches is therefore public.

## Decision

1. **The staff list becomes a pipeline source like any other.** A new connector, `unza_staff`, fetches a staff list that holds only public columns: `Surname, First Name, Second Name, Title, Occupation, School`. The source sheet has no staff IDs, because raw records are published (Context). As a guard, the connector also keeps only those six columns and drops any other one the sheet may gain, logging the column name only. The list is a tab of the team's staff sheet, published as CSV; its address is the variable `UNZA_STAFF_LIST_URL` (listed in `.env.example` and passed to the Pipeline workflow). Without it the connector fetches nothing and the pipeline still runs.
2. **dbt models it like every other source.** `stg_unza_staff__staff` tidies whitespace and drops rows without a surname. `dim_staff` in the research mart holds one row per person: `staff_key` and the six public columns. School labels are kept as written and mapped to units in one place, `ihub.staff.roster.SCHOOL_BY_LABEL`, which the local CSV also uses.
3. **A person's identity is a key built from public data, never a staff ID.** `ihub.staff.roster.staff_key` hashes the name parts and school label, so the same person gets the same key, and the same Members URL, from the local CSV and from the mart. Two rows with the same name and school get distinct keys and so are never merged (ADR-014). The overrides file (`staff_author_overrides.csv`) is keyed by this `Staff key` instead of the HR staff ID; `scripts/staff_near_misses.py` prints it.
4. **The matching code depends on a roster source, not on a file** (dependency inversion). `ihub.staff.sources` defines `RosterSource`, with two implementations: `CsvRosterSource` (the local file and its overrides, for development) and `MartRosterSource` (reads `marts.dim_staff` through `ihub.mart.staff_links`, so no SQL is in the routes). The API calls `choose_roster` per request: the CSV if it is present, otherwise the mart if it has staff, otherwise none. The matching, attribution and Members code are unchanged apart from the `staff_key` rename, and a later HR system is one more `RosterSource`.
5. **Access control is unchanged.** Named staff are still served only under `members:read`, and the directory is still A to Z with no ranking.

## Consequences

- Members and the school credit work on Cloud Run after the next pipeline run, with no private file in production.
- The staff list is now public, as part of the data release. This is acceptable only because it holds information UNZA already publishes; the ADR-009 Data Protection Act, 2021 question is answered for these columns only. Any other column (Staff ID, grade, salary, contract) stays out and needs its own ADR.
- A person whose name or school changes gets a new `staff_key`, so their Members link changes and any override pinned to them must be re-pinned. Existing override files keyed by Staff ID must be rewritten with staff keys.
- Production has no overrides file yet, so people the name matching cannot connect stay unlisted there until overrides get a public home (a later decision).
- Someone must keep the public tab in step with the roster.

## Alternatives considered

- **Load the full roster CSV into DuckDB.** Rejected: the Staff ID would be published in the data release.
- **Drop the Staff ID in dbt staging.** Rejected: the raw schema is published too.
- **A private Cloud Storage bucket mounted into the API container.** Keeps the roster private, but treats public data as secret and needs a separate upload outside the pipeline. It is still the right route for any non-public HR column later.
- **Map school labels in a dbt seed.** Deferred: the API image does not contain `transform/`, so the local CSV path would need its own copy of the mapping.
- **Commit the staff list as a dbt seed.** Rejected: the repository does not hold data files (`CLAUDE.md`).
