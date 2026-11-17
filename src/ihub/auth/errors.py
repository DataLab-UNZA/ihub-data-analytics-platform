"""Authentication errors. Each carries the HTTP status and the message a user may see.

Messages never contain tokens, codes or other people's details.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base class: ``status_code``, a public ``message``, optional headers and audit reason."""

    status_code = 400

    def __init__(
        self,
        message: str,
        *,
        headers: dict[str, str] | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.headers = headers or {}
        self.reason = reason or type(self).__name__


class AuthNotConfiguredError(AuthError):
    """Authentication cannot run here (missing secret, or no persistent user store)."""

    status_code = 503


class MethodUnavailableError(AuthError):
    """This sign-in method is not set up (no Google client, or no email sender)."""

    status_code = 503


class NotAuthenticatedError(AuthError):
    """No access token was sent."""

    status_code = 401

    def __init__(self, message: str = "Sign in to continue.") -> None:
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class InvalidTokenError(AuthError):
    """The access or refresh token is invalid, expired or revoked."""

    status_code = 401

    def __init__(self, message: str = "Your session has ended. Sign in again.") -> None:
        super().__init__(message, headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})


class PermissionDeniedError(AuthError):
    """The signed-in user's role does not grant the permission a route needs."""

    status_code = 403


class IdentityRejectedError(AuthError):
    """The identity is valid but not allowed here (wrong domain, unverified email)."""

    status_code = 403


class AccountDeactivatedError(AuthError):
    """An administrator has deactivated this account."""

    status_code = 403


class InvalidEmailError(AuthError):
    """The address is malformed or not at the allowed domain."""

    status_code = 400


class InvalidCodeError(AuthError):
    """The email sign-in code is wrong, used, expired or out of attempts."""

    status_code = 400


class InvalidRequestError(AuthError):
    """A malformed or tampered sign-in request (for example a bad OAuth state)."""

    status_code = 400


class RateLimitedError(AuthError):
    """Too many requests; ``retry_after`` seconds until the next one is allowed."""

    status_code = 429

    def __init__(self, message: str, retry_after: int) -> None:
        super().__init__(message, headers={"Retry-After": str(max(1, retry_after))})
        self.retry_after = max(1, retry_after)


class NotFoundError(AuthError):
    """The user (or other record) does not exist."""

    status_code = 404


class ConflictError(AuthError):
    """A user change that would break an invariant (for example: no administrator left)."""

    status_code = 409


class UpstreamError(AuthError):
    """Google or the mail server failed."""

    status_code = 502
