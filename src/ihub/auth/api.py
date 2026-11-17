"""FastAPI layer for authentication (ADR-010): dependencies and routes.

- ``current_principal`` reads ``Authorization: Bearer <access token>`` (401 without one).
- ``require(permission)`` adds the RBAC check (403 when the role lacks the permission).
- ``/api/auth/*``: sign in with Google or an email code, refresh, sign out, who am I.
- ``/api/admin/*``: users, roles and audit events, for holders of ``users:manage``.

Token responses are marked ``Cache-Control: no-store``. The routes are only reachable
through the Next.js server (the API is a private sidecar), never from a browser directly.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ihub.auth.errors import InvalidRequestError, NotAuthenticatedError, PermissionDeniedError
from ihub.auth.models import AuthEvent, Principal, User, UserStatus
from ihub.auth.profile import MAX_AVATAR_BYTES
from ihub.auth.rbac import ROLE_PERMISSIONS, Permission, Role
from ihub.auth.service import AuthService, SignInResult

AuthServiceProvider = Callable[[], AuthService]

_bearer = HTTPBearer(auto_error=False, description="Access token from /api/auth/*")


# Dependencies --------------------------------------------------------------------------


def get_auth_service(request: Request) -> AuthService:
    """The service, built on first use (raises AuthNotConfiguredError, a 503, if it cannot)."""
    provider: AuthServiceProvider = request.app.state.auth_service
    return provider()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    service: AuthServiceDep,
) -> Principal:
    """The caller behind a valid bearer access token."""
    if credentials is None:
        raise NotAuthenticatedError()
    return service.principal(credentials.credentials)


PrincipalDep = Annotated[Principal, Depends(current_principal)]


def require(permission: Permission) -> Callable[..., Principal]:
    """A dependency that admits only callers whose role grants ``permission``."""

    def dependency(principal: PrincipalDep) -> Principal:
        if not principal.has(permission):
            raise PermissionDeniedError("Your role does not allow this.", reason=permission.value)
        return principal

    dependency.__name__ = f"require_{permission.name.lower()}"
    return dependency


def current_admin(principal: PrincipalDep, service: AuthServiceDep) -> Principal:
    """The caller, who must hold ``users:manage`` according to the store, not just the token.

    Administration re-reads the role, so demoting an administrator takes effect at once
    rather than when their access token expires.
    """
    user = service.current_user(principal)
    if Permission.USERS_MANAGE not in user.permissions:
        raise PermissionDeniedError("Your role does not allow this.", reason="users:manage")
    return Principal(user_id=user.user_id, email=user.email, role=user.role)


AdminDep = Annotated[Principal, Depends(current_admin)]


# Request and response bodies ------------------------------------------------------------


class GoogleStartIn(BaseModel):
    next: str | None = Field(default=None, max_length=512)


class GoogleStartOut(BaseModel):
    authorization_url: str
    flow: str
    flow_expires_in: int


class GoogleCallbackIn(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(min_length=1, max_length=256)
    flow: str = Field(min_length=1, max_length=4096)


class EmailCodeRequestIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class EmailCodeSentOut(BaseModel):
    expires_in: int
    resend_after: int


class EmailCodeVerifyIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=1, max_length=16)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    email: str
    name: str | None
    role: Role
    status: UserStatus
    permissions: list[Permission]
    created_at: datetime
    last_sign_in_at: datetime | None
    phone: str | None = None
    avatar_updated_at: datetime | None = None

    @classmethod
    def of(cls, user: User) -> UserOut:
        return cls(
            id=user.user_id,
            email=user.email,
            name=user.name,
            role=user.role,
            status=user.status,
            permissions=sorted(user.permissions),
            created_at=user.created_at,
            last_sign_in_at=user.last_sign_in_at,
            phone=user.phone,
            avatar_updated_at=user.avatar_updated_at,
        )


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)


class EmailChangeIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class EmailChangeVerifyIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=1, max_length=16)


class TokenOut(BaseModel):
    token_type: str = "bearer"
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    next: str
    user: UserOut

    @classmethod
    def of(cls, result: SignInResult) -> TokenOut:
        return cls(
            access_token=result.access_token,
            expires_in=result.access_expires_in,
            refresh_token=result.refresh_token,
            refresh_expires_in=result.refresh_expires_in,
            next=result.next_path,
            user=UserOut.of(result.user),
        )


class MethodsOut(BaseModel):
    google: bool
    email_code: bool
    allowed_domain: str


class UserUpdateIn(BaseModel):
    role: Role | None = None
    status: UserStatus | None = None


class RoleOut(BaseModel):
    role: Role
    permissions: list[Permission]


class AuditEventOut(BaseModel):
    kind: str
    occurred_at: datetime
    user_id: str | None
    actor_id: str | None
    detail: str | None

    @classmethod
    def of(cls, event: AuthEvent) -> AuditEventOut:
        return cls(
            kind=event.kind,
            occurred_at=event.occurred_at,
            user_id=event.user_id,
            actor_id=event.actor_id,
            detail=event.detail,
        )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


# Routes ---------------------------------------------------------------------------------


def build_auth_router() -> APIRouter:
    """Sign-in, token and identity routes under ``/api/auth``."""
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.get("/methods")
    def methods(service: AuthServiceDep) -> MethodsOut:
        """Which sign-in methods are available, for the sign-in screen."""
        return MethodsOut(**service.methods, allowed_domain=service.allowed_domain)

    @router.post("/google/start")
    def google_start(
        body: GoogleStartIn, service: AuthServiceDep, response: Response
    ) -> GoogleStartOut:
        """Begin Google sign-in: where to send the browser, and the flow state to keep."""
        _no_store(response)
        start = service.start_google(body.next)
        return GoogleStartOut(
            authorization_url=start.authorization_url,
            flow=start.flow,
            flow_expires_in=start.flow_expires_in,
        )

    @router.post("/google/callback")
    def google_callback(
        body: GoogleCallbackIn, service: AuthServiceDep, response: Response
    ) -> TokenOut:
        """Finish Google sign-in with the code and state Google returned."""
        _no_store(response)
        return TokenOut.of(service.finish_google(code=body.code, state=body.state, flow=body.flow))

    @router.post("/email/request", status_code=status.HTTP_202_ACCEPTED)
    def email_request(body: EmailCodeRequestIn, service: AuthServiceDep) -> EmailCodeSentOut:
        """Send a one-time sign-in code to a UNZA email address."""
        sent = service.request_email_code(body.email)
        return EmailCodeSentOut(expires_in=sent.expires_in, resend_after=sent.resend_after)

    @router.post("/email/verify")
    def email_verify(
        body: EmailCodeVerifyIn, service: AuthServiceDep, response: Response
    ) -> TokenOut:
        """Sign in with the emailed code."""
        _no_store(response)
        return TokenOut.of(service.finish_email_code(email=body.email, code=body.code))

    @router.post("/refresh")
    def refresh(body: RefreshIn, service: AuthServiceDep, response: Response) -> TokenOut:
        """Swap a refresh token for a new token pair (the old refresh token is rotated)."""
        _no_store(response)
        return TokenOut.of(service.refresh(body.refresh_token))

    @router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
    def sign_out(body: RefreshIn, service: AuthServiceDep) -> None:
        """End the session the refresh token belongs to. Always succeeds."""
        service.sign_out(body.refresh_token)

    @router.get("/me")
    def me(principal: PrincipalDep, service: AuthServiceDep, response: Response) -> UserOut:
        """The signed-in user, with the permissions their role grants."""
        _no_store(response)
        return UserOut.of(service.current_user(principal))

    @router.patch("/me")
    def update_me(body: ProfileIn, principal: PrincipalDep, service: AuthServiceDep) -> UserOut:
        """Change your own name or phone."""
        return UserOut.of(service.update_profile(principal, name=body.name, phone=body.phone))

    @router.put("/me/avatar")
    async def put_avatar(
        request: Request, principal: PrincipalDep, service: AuthServiceDep
    ) -> UserOut:
        """Upload your profile photo as the raw request body (PNG, JPEG or WebP, 2 MB)."""
        declared = int(request.headers.get("content-length") or 0)
        if declared > MAX_AVATAR_BYTES:
            raise InvalidRequestError("The photo must be 2 MB or smaller.", reason="too_large")
        data = b""
        async for chunk in request.stream():
            data += chunk
            if len(data) > MAX_AVATAR_BYTES:
                raise InvalidRequestError("The photo must be 2 MB or smaller.", reason="too_large")
        return UserOut.of(service.set_avatar(principal, data))

    @router.get("/me/avatar")
    def get_avatar(principal: PrincipalDep, service: AuthServiceDep) -> Response:
        """Your profile photo (404 when there is none)."""
        avatar = service.avatar(principal)
        return Response(
            content=avatar.data,
            media_type=avatar.content_type,
            headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
        )

    @router.delete("/me/avatar")
    def delete_avatar(principal: PrincipalDep, service: AuthServiceDep) -> UserOut:
        return UserOut.of(service.remove_avatar(principal))

    @router.post("/me/email/request", status_code=status.HTTP_202_ACCEPTED)
    def email_change_request(
        body: EmailChangeIn, principal: PrincipalDep, service: AuthServiceDep
    ) -> EmailCodeSentOut:
        """Send a code to the new address; nothing changes until it is confirmed."""
        sent = service.request_email_change(principal, body.email)
        return EmailCodeSentOut(expires_in=sent.expires_in, resend_after=sent.resend_after)

    @router.post("/me/email/verify")
    def email_change_verify(
        body: EmailChangeVerifyIn, principal: PrincipalDep, service: AuthServiceDep
    ) -> UserOut:
        """Switch to the new address with the code sent to it."""
        return UserOut.of(
            service.confirm_email_change(principal, new_email=body.email, code=body.code)
        )

    return router


def build_admin_router() -> APIRouter:
    """User and role administration under ``/api/admin``; needs ``users:manage``."""
    router = APIRouter(prefix="/api/admin", tags=["admin"])

    @router.get("/users")
    def list_users(_: AdminDep, service: AuthServiceDep) -> list[UserOut]:
        return [UserOut.of(user) for user in service.list_users()]

    @router.patch("/users/{user_id}")
    def update_user(
        user_id: str,
        body: UserUpdateIn,
        service: AuthServiceDep,
        actor: AdminDep,
    ) -> UserOut:
        """Change a user's role or status. At least one active administrator must remain."""
        updated = service.update_user(actor, user_id, role=body.role, status=body.status)
        return UserOut.of(updated)

    @router.get("/roles")
    def roles(_: AdminDep) -> list[RoleOut]:
        """The RBAC table: each role and its permissions."""
        return [
            RoleOut(role=role, permissions=sorted(permissions))
            for role, permissions in ROLE_PERMISSIONS.items()
        ]

    @router.get("/audit")
    def audit(
        _: AdminDep,
        service: AuthServiceDep,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[AuditEventOut]:
        """Recent sign-ins and access changes, newest first."""
        return [AuditEventOut.of(event) for event in service.recent_events(limit)]

    return router
