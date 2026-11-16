# ADR-008: Staff sign in with their UNZA Google Workspace account

- **Status:** Proposed
- **Date:** November 16, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

The Next.js front end ([ADR-005](ADR-005-nextjs-frontend.md), [ADR-007](ADR-007-nextjs-only-front-end.md)) has sign-in screens that only mirror the designs. They have passwords, one-time codes and a workspace chooser, but no real authentication. Members of staff should register and sign in with their UNZA email. UNZA mail runs on Google Workspace, and staff addresses end in `@unza.ac.zm`.

The platform should hold no passwords. A domain check on the client alone can be bypassed: Google's `hd` request parameter only filters the account chooser.

## Decision

1. **Sign-in uses Google OpenID Connect through Auth.js in Next.js**, with the Google provider and `hd=unza.ac.zm` as a hint. There are no passwords, one-time codes or invitation screens. Those mock screens are removed.
2. **FastAPI owns identity and registration.** After Google signs a user in, Next.js sends the Google ID token to `POST /api/auth/exchange`. FastAPI accepts the token only if all of these hold:
   - the signature is valid
   - `aud` is our client ID
   - `iss` is Google
   - `email_verified` is true
   - the `hd` claim equals `IHUB_ALLOWED_DOMAIN` (`unza.ac.zm`)

   The first accepted sign-in **registers** the user with the role `member`. Any other account goes to the "access restricted" screen.
3. **Sessions.** Auth.js keeps the session, including the user's role, in an encrypted, httpOnly, secure cookie. Each server-side call from Next.js to the API carries a 60-second HS256 token signed with `IHUB_INTERNAL_TOKEN_SECRET`. FastAPI checks it in a `current_user` dependency and authorises with `require_role(...)`.
4. **Roles.** The roles are `member`, `analyst`, `librarian`, `unit-head`, `executive` and `admin`, the same as `web/src/config/roles.js`, which stops being a free role switcher. Admins change roles on the users screen. `IHUB_BOOTSTRAP_ADMINS` (a list of emails) names the first admins.
5. **Access.** Every research screen and route needs a signed-in user. Administration needs `admin`. `/api/health` stays open for the Cloud Run health check.
6. **Abstractions.** The token check sits behind an `IdentityVerifier` interface, with `GoogleIdTokenVerifier` as the implementation. Moving to Microsoft Entra ID or Keycloak later means one new class and no route changes.
7. **Secrets.**
   - The variable names `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `IHUB_INTERNAL_TOKEN_SECRET`, `IHUB_ALLOWED_DOMAIN` and `IHUB_BOOTSTRAP_ADMINS` are listed in `.env.example`.
   - Production values live in Google Secret Manager and are mounted into Cloud Run. They are never committed and never printed in logs.
   - The OAuth client is created in the project's Google Cloud project. The consent screen is *Internal* if that project belongs to the UNZA Workspace organisation, and *External* otherwise; the server-side domain check applies in both cases.

## Consequences

- Staff need no new password, and leavers lose access when UNZA disables their Google account.
- Research data, which is public anyway, sits behind sign-in. If public reading is wanted later, it is a per-route choice.
- Tests cover a wrong domain, an unverified email, an expired or tampered internal token, and a non-admin calling an admin route. They use fake verifiers and never call Google.
- Signed-in users must be stored somewhere. [ADR-009](ADR-009-user-store-and-staff-data.md) records where.

## Alternatives considered

- **Email and password.** We would have to store passwords and handle resets, which the platform should not do.
- **Microsoft Entra ID.** UNZA staff mail is on Google Workspace, so Entra is not needed now. The `IdentityVerifier` interface keeps that option open.
- **Forwarding the Google ID token on every API call.** The token lasts an hour and would need refreshing in the browser session. A short-lived internal token is simpler.
