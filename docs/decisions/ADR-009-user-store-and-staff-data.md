# ADR-009: A private store for users and the staff roster

- **Status:** Proposed
- **Date:** November 16, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

Two kinds of personal data arrive with staff sign-in ([ADR-008](ADR-008-staff-sign-in-with-google.md)):

- **User accounts:** email, name, role, status, and first and last sign-in.
- **The staff roster:** a spreadsheet, provided later, with each staff member's name, title, school and department.

`CLAUDE.md` requires sensitive sources to have private storage and access control, recorded in an ADR before any work starts. They must never be published as release assets or printed in public workflow logs.

The research database `ihub.duckdb` cannot hold this data. It is rebuilt every week, published as a **public** GitHub Release asset, and built into a read-only image. The application also needs somewhere it can write.

## Decision

1. **Users and the roster live in Firestore** (Native mode) in the project's Google Cloud project, in the same region as Cloud Run. They never go into `ihub.duckdb`, the repository, release assets or workflow logs.
2. **Access is keyless and minimal.** Only the Cloud Run runtime service account has `roles/datastore.user`. No key file exists. In local development, the Firestore emulator or an in-memory store is used.
3. **The code depends on interfaces, not on Firestore.** `UserRepository` and `StaffRosterRepository` are small protocols in `ihub.auth` and `ihub.staff`, with Firestore and in-memory implementations. FastAPI injects the implementation with `Depends`, and tests use the in-memory one. Moving to Cloud SQL for PostgreSQL later means writing one new class.
4. **How the roster is imported.**
   - An admin uploads the spreadsheet as CSV through `POST /api/admin/staff-roster`.
   - Each row is validated with pydantic: name, title, school, department and UNZA email. Rejected rows are reported to the admin and are not logged.
   - Rows link to users by exact lower-cased email.
   - Rows link to `dim_author` by ORCID first, then by normalised name. Name matches are only candidates: an admin confirms them in the data-quality review queue.
5. **Uses.** The roster may supply staff titles, membership of schools and departments, and headcounts per school. The rules in `CLAUDE.md` still apply: no individual staff rankings and no h-index league tables.
6. **Retention.** Re-uploading the roster replaces it. An admin can deactivate a user, and deactivated users cannot sign in.

## Consequences

- No personal data enters the public data release. The pipeline workflow is unchanged.
- One more managed service. Firestore's free tier (1 GiB stored, 50,000 reads and 20,000 writes a day) is far above what the prototype needs, and it costs nothing when idle.
- Queries that combine research and staff data, such as headcount per school next to output, are joined in the API layer and not in SQL. That is acceptable at UNZA's scale.
- The data controller's obligations under Zambia's Data Protection Act, 2021 must be confirmed with UNZA before real roster data is uploaded. Until then, only synthetic test data is used.

## Alternatives considered

- **A table in `ihub.duckdb`.** Rejected: the file is public and read-only.
- **Cloud SQL for PostgreSQL.** Relational and familiar, but the smallest instance has a monthly cost even when idle. It stays the upgrade path behind the repository interfaces.
- **A Google Sheet read at runtime.** Easy to edit, but access control and validation would sit outside the application.
