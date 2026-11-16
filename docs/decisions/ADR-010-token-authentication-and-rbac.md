# ADR-010: Token-based sign-in with Google or an email code, and role-based access control

- **Status:** Proposed
- **Date:** November 16, 2026
- **Decided by:** the team; for review by Lighton Phiri

## Context

[ADR-008](ADR-008-staff-sign-in-with-google.md) chose Google sign-in through Auth.js in Next.js. In that design, Next.js held the session and sent FastAPI a 60-second internal token. The team now wants three things:

- **Token-based authentication issued by our own backend**, not a session held by a front-end library.
- **A second, email-based way to sign in.** The designs already include a "Check your email" code screen.
- **Role-based access control (RBAC)** that the API enforces.

The rules from ADR-008 still hold: only `@unza.ac.zm` accounts, no stored passwords, and FastAPI owns identity.

## Decision

1. **FastAPI is the token issuer** (`src/ihub/auth/`).
   - **Access token:** a JWT signed with HS256, lasting 15 minutes. Claims: `iss`, `aud`, `sub` (user ID), `email`, `role`, `iat`, `exp`, `jti`.
   - **Refresh token:** an opaque 256-bit random value lasting 7 days. A session (a "family" of refresh tokens) lasts at most 30 days.
   - Only a SHA-256 hash of each refresh token is stored.
   - Every refresh **rotates** the token. If an already-rotated token is presented more than 20 seconds after rotation, the whole family is revoked, because that signals a stolen token. The 20-second window lets parallel requests share one rotation.
   - Signing out revokes the family. Deactivating a user revokes all of that user's families.
   - Every refresh re-reads the user, so a role change or deactivation applies within 15 minutes.
2. **Two ways to prove ownership of a UNZA email address.** Both end in the same token pair.
   - **Google OAuth 2.0 / OpenID Connect**, using the authorisation-code flow with PKCE (S256), `state` and `nonce`, and `hd=unza.ac.zm` as a hint. FastAPI exchanges the code itself, using the client secret. It then checks the ID token's signature against Google's JWKS, plus `iss`, `aud`, `exp`, `nonce` and `email_verified`. It also checks that the `hd` claim and the email domain equal `IHUB_ALLOWED_EMAIL_DOMAIN`. The redirect URI comes from `IHUB_PUBLIC_URL` and is never taken from the request.
   - **Email one-time code:**
     - Six digits from `secrets`, valid for 10 minutes and usable once.
     - At most 5 wrong attempts per code, and requesting a new code replaces the old one.
     - At most one code every 30 seconds and five an hour per address.
     - Codes are stored as an HMAC under a server-side key, so a copy of the store cannot be brute-forced offline.
     - Codes are sent over SMTP (any provider) and never logged in production. In development a console sender prints them.
3. **Registration.** The first successful sign-in with an allowed address creates the user with the role `member`. Addresses listed in `IHUB_BOOTSTRAP_ADMINS` are made `admin` at every sign-in. This way the first administrators cannot lock themselves out.
4. **RBAC.** Routes depend on **permissions**, never on role names. A single table, in `src/ihub/auth/rbac.py`, maps each role to its permissions:

   | Role | Permissions |
   |---|---|
   | member | `research:read` |
   | analyst | `research:read`, `research:export`, `reports:manage` |
   | librarian | `research:read`, `research:export`, `quality:review` |
   | unit-head | `research:read`, `research:export`, `reports:manage` |
   | executive | `research:read`, `research:export`, `reports:manage` |
   | admin | all of the above, `sources:manage`, `users:manage` |

   - A missing or invalid token gets `401`, and a missing permission gets `403`.
   - Administrators manage users through `/api/admin/users`. These routes re-read the caller's role from the store rather than trusting the access token, so demoting an administrator takes effect at once.
   - The API refuses any change that would leave no active administrator, including demoting or deactivating oneself.
   - Sign-ins, refused sign-ins, role and status changes, and refresh-token reuse are recorded as audit events.
   - Limiting unit heads to their own unit is left for a later ADR.
5. **Next.js is a backend-for-frontend.** The browser never sees a token. Next.js route handlers drive the sign-in flows and keep the tokens in `httpOnly`, `Secure`, `SameSite=Lax` cookies. `src/proxy.js` refreshes an expired access token and sends signed-out users to `/login`. Server code forwards the access token to the API as `Authorization: Bearer`. **Auth.js is not used.**
6. **Secrets and keys.**
   - One secret, `IHUB_AUTH_SECRET`, at least 32 bytes. Separate keys are derived from it (HMAC-SHA256) for access tokens, OAuth flow state and email codes.
   - Further settings: `IHUB_GOOGLE_CLIENT_ID`, `IHUB_GOOGLE_CLIENT_SECRET`, `IHUB_PUBLIC_URL`, `IHUB_ALLOWED_EMAIL_DOMAIN`, `IHUB_BOOTSTRAP_ADMINS`, and `IHUB_SMTP_*`.
   - `IHUB_ENV` defaults to `production`. Only `IHUB_ENV=development` allows a generated, temporary secret and the console email sender.
   - If authentication is not configured, the auth routes answer `503`. The research routes are unaffected.
7. **Storage** follows [ADR-009](ADR-009-user-store-and-staff-data.md). Users, refresh-token hashes, email-code hashes and audit events sit behind small repository interfaces.
   - A SQLite implementation serves tests and local development.
   - Production needs a persistent store (Firestore, per ADR-009). Until it exists, the API refuses to run authentication in production on SQLite, because Cloud Run's disk is temporary.

## Consequences

- One identity model for both sign-in methods. Adding Microsoft Entra ID or SAML later means one new verifier class.
- A stolen access token is useful for at most 15 minutes. A stolen refresh token is caught when it is reused.
- The email method needs a sending mailbox, for example a UNZA no-reply address with SMTP access. That must be arranged with UNZA ICT before the email option is turned on in production.
- The work is split into pull requests:
  1. the backend (this ADR, `ihub.auth`, the auth and admin routes);
  2. the Next.js flows, the cookies, and protecting every research route;
  3. the production store (Firestore) and secrets in Secret Manager.

## Alternatives considered

- **Auth.js sessions (ADR-008).** It works, but the session would belong to the front-end library, and adding the email-code flow and RBAC would happen in two places.
- **Tokens in browser storage.** Any XSS bug could read them. `httpOnly` cookies cannot be read by scripts.
- **Stateless refresh tokens (JWT).** They cannot be revoked, and reuse cannot be detected.
- **Email and password.** Rejected in ADR-008: the platform should not store passwords.
