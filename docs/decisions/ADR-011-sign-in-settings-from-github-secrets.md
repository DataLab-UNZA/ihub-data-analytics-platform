# ADR-011: Pass the sign-in settings to Cloud Run from GitHub secrets and variables

- **Status:** Proposed
- **Date:** November 17, 2026
- **Decided by:** Bruce Mainza; for review by the team and Lighton Phiri

## Context

Sign-in (ADR-010) needs credentials in the live app: the token-signing secret, the Google OAuth client and an SMTP mailbox. [ADR-008](ADR-008-staff-sign-in-with-google.md) planned to keep the production values in Google Secret Manager, mounted into Cloud Run. Secret Manager is not set up yet, and setting it up needs the project owner in Cloud Shell. The connector credentials already follow a working pattern: GitHub environment secrets that only `main` can read, passed to the workflow that needs them.

## Decision

1. **Secrets** (`IHUB_AUTH_SECRET`, `IHUB_GOOGLE_CLIENT_SECRET`, `IHUB_SMTP_PASSWORD`) are **environment secrets of both `production` and `pipeline`**, because the Deploy job runs in `production` for a merge or a manual deploy and in `pipeline` for the weekly redeploy.
2. **Non-secret settings** (`IHUB_GOOGLE_CLIENT_ID`, `IHUB_SMTP_HOST`, `IHUB_SMTP_PORT`, `IHUB_SMTP_USERNAME`, `IHUB_SMTP_FROM`, `IHUB_SMTP_SSL`, `IHUB_ALLOWED_EMAIL_DOMAIN`, `IHUB_BOOTSTRAP_ADMINS`, optionally `IHUB_PUBLIC_URL`) are **repository variables**.
3. `deploy.yml` writes each value that is set into the `api` container of `deploy/service.yaml`, quoted as a JSON string so no character can break the YAML. Unset values are left out, so the deploy works before any of them exist. `IHUB_PUBLIC_URL` defaults to the service's own address.
4. The rendered service file stays in the runner's temporary folder and is never printed or uploaded; GitHub masks the secrets in logs.

## Consequences

- The credentials reach the live app with no new Google Cloud set-up, using the same GitHub pattern as the connectors.
- Values set as Cloud Run environment variables are visible to anyone who can view the service in Google Cloud. That is weaker than Secret Manager, which remains the target (ADR-008). Moving there later changes only `deploy/service.yaml` and `deploy.yml`.
- The running app now holds secrets, which updates the statement in ADR-002 that it needs none.
- Production sign-in still stays off: `IHUB_REQUIRE_SIGN_IN=false` remains, and the API refuses to enable sign-in in production until the persistent user store exists (ADR-009). This decision only puts the credentials in place for that moment.
