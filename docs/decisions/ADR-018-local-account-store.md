# ADR-018: Keep accounts in a local database inside the app, not Firestore

- **Status:** Proposed
- **Date:** November 24, 2026
- **Decided by:** Bruce Mainza; for review by the team and Lighton Phiri
- **Supersedes:** [ADR-016](ADR-016-firestore-user-store-in-production.md)

## Context

ADR-016 moved accounts to Firestore. The team does not want a managed cloud datastore for this prototype: everything should run inside the app, with the research data in DuckDB as before.

## Decision

1. Accounts, sessions, email codes and profile photos are kept in the existing SQLite store, a single file inside the `api` container (`/tmp/ihub-auth.sqlite`), with `IHUB_ALLOW_EPHEMERAL_AUTH=true`. SQLite is used rather than DuckDB because it is built for many small writes, and rather than PostgreSQL because that needs a separate server.
2. The Firestore store, its tests and the `google-cloud-firestore` dependency are removed.
3. The research data stays in DuckDB, built by the pipeline and baked into the image.

## Consequences

- No Google Cloud database or IAM set-up is needed.
- Cloud Run's disk is temporary. Accounts are erased when the instance is replaced: after a deploy, a restart or scaling to zero when idle. People then sign in again; addresses in `IHUB_BOOTSTRAP_ADMINS` get the administrator role back at sign-in, but roles given by hand are lost.
- The service runs at most one instance (`maxScale: 1`), so everyone shares one account file.
- For durable accounts later, a store that survives restarts is needed (a PostgreSQL server or a managed database); the code depends only on the protocols in `ihub.auth.store`.
