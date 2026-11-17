# ADR-012: Keep users in Firestore and require sign-in in production

- **Status:** Proposed
- **Date:** November 17, 2026
- **Decided by:** Bruce Mainza; for review by the team and Lighton Phiri

## Context

ADR-009 chose Firestore for the user store, but only the SQLite store existed, so the API refused sign-in in production and `deploy/service.yaml` kept `IHUB_REQUIRE_SIGN_IN=false`. The Google OAuth and SMTP credentials are now in place (ADR-011).

## Decision

1. `ihub.auth.firestore_store.FirestoreAuthStore` implements the store protocols (`ihub.auth.store`) over Firestore (Native mode), selected with `IHUB_AUTH_STORE=firestore`. It uses the runtime service account, so there are no keys.
2. Queries use only equality filters on one field and ordering by one field, so Firestore's automatic indexes are enough.
3. A Firestore document holds at most 1 MiB, so profile photos (up to 2 MB) are split into 900 kB chunk documents.
4. Production refuses the SQLite store. `deploy/service.yaml` sets `IHUB_AUTH_STORE=firestore` and no longer turns sign-in off.
5. Tests use an in-memory fake Firestore client and never call Google.

## Consequences

- Before this is deployed, the project owner must create the database and grant access once, in Cloud Shell:
  `gcloud firestore databases create --location=africa-south1` and
  `gcloud projects add-iam-policy-binding <project> --member=serviceAccount:<runtime SA> --role=roles/datastore.user`.
- Sign-in now needs a valid `IHUB_ALLOWED_EMAIL_DOMAIN` (for example `unza.ac.zm`). Production refuses `*`.
- Saved charts and dashboards (`ihub.workspace`) are still in SQLite, so they are lost when the instance restarts. Moving them is a separate change.
