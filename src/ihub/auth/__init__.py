"""Authentication and role-based access control (ADR-010).

FastAPI issues its own tokens after a user proves they own a UNZA email address, either
with Google (OpenID Connect) or with a one-time code sent by email. Routes are protected
by permissions, which come from the user's role (:mod:`ihub.auth.rbac`).

Modules, one concern each:

- ``errors``       the exceptions the API turns into 4xx/5xx responses
- ``rbac``         roles, permissions and the table that links them
- ``models``       users, refresh-token records, email challenges, audit events
- ``store``        the repository interfaces; ``sqlite_store`` implements them
- ``tokens``       access tokens (JWT), refresh-token rotation, signed OAuth flow state
- ``email_codes``  one-time sign-in codes and the senders that deliver them
- ``google``       the Google OpenID Connect client and ID-token checks
- ``service``      the use cases: sign in, refresh, sign out, manage users
- ``factory``      builds the service from settings
- ``api``          FastAPI dependencies (``current_principal``, ``require``) and routes
"""
