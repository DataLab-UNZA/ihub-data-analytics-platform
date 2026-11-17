"""Authentication use cases (ADR-010): sign in, refresh, sign out, and manage users.

Both sign-in methods prove that the caller owns an address at the allowed domain and then
share one path, :meth:`AuthService._sign_in`: register on first sign-in, refuse deactivated
accounts, apply bootstrap administrators, record an audit event and issue tokens.
"""

from __future__ import annotations

import hmac
import secrets
import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from ihub.auth.config import AuthConfig, Clock
from ihub.auth.email_codes import EmailCodeService
from ihub.auth.errors import (
    AccountDeactivatedError,
    ConflictError,
    IdentityRejectedError,
    InvalidRequestError,
    InvalidTokenError,
    MethodUnavailableError,
    NotFoundError,
    PermissionDeniedError,
)
from ihub.auth.google import GoogleOAuthClient
from ihub.auth.models import AuthEvent, Avatar, Principal, SignInMethod, User, UserStatus
from ihub.auth.profile import clean_name, clean_phone, image_type
from ihub.auth.rbac import DEFAULT_ROLE, Permission, Role
from ihub.auth.store import AuthStore
from ihub.auth.tokens import (
    USER_DEACTIVATED,
    RefreshTokenReuseError,
    TokenService,
    pkce_pair,
)

DEFAULT_NEXT_PATH = "/overview"


def safe_next_path(value: str | None) -> str:
    """A same-site path to return to after sign-in; anything else becomes the overview.

    Rejects absolute and protocol-relative URLs, backslashes and control characters, so the
    sign-in flow cannot be used as an open redirect.
    """
    if (
        not value
        or not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        return DEFAULT_NEXT_PATH
    return value


@dataclass(frozen=True)
class SignInResult:
    """Tokens for a signed-in user. The refresh token exists in clear only here."""

    user: User
    access_token: str
    access_expires_in: int
    refresh_token: str
    refresh_expires_in: int
    next_path: str = DEFAULT_NEXT_PATH


@dataclass(frozen=True)
class GoogleSignInStart:
    """Where to send the browser, and the signed flow state to keep until the callback."""

    authorization_url: str
    flow: str
    flow_expires_in: int


@dataclass(frozen=True)
class EmailCodeSent:
    """How long the code lasts and when another may be requested (seconds)."""

    expires_in: int
    resend_after: int


class AuthService:
    """The only entry point the API routes use."""

    def __init__(
        self,
        config: AuthConfig,
        store: AuthStore,
        *,
        tokens: TokenService,
        email_codes: EmailCodeService,
        google: GoogleOAuthClient | None,
        clock: Clock,
    ) -> None:
        self._config = config
        self._store = store
        self._tokens = tokens
        self._email_codes = email_codes
        self._google = google
        self._clock = clock

    @property
    def allowed_domain(self) -> str:
        return self._config.allowed_domain

    @property
    def methods(self) -> dict[str, bool]:
        """Which sign-in methods are set up here (for the sign-in screen)."""
        return {"google": self._google is not None, "email_code": self._email_codes.available}

    # Google ----------------------------------------------------------------------------

    def start_google(self, next_path: str | None = None) -> GoogleSignInStart:
        google = self._require_google()
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        verifier, challenge = pkce_pair()
        flow = self._tokens.sign_flow(
            {
                "state": state,
                "nonce": nonce,
                "verifier": verifier,
                "next": safe_next_path(next_path),
            }
        )
        return GoogleSignInStart(
            authorization_url=google.authorization_url(
                state=state, nonce=nonce, code_challenge=challenge
            ),
            flow=flow,
            flow_expires_in=self._tokens.flow_ttl_seconds,
        )

    def finish_google(self, *, code: str, state: str, flow: str) -> SignInResult:
        google = self._require_google()
        data = self._tokens.read_flow(flow)
        expected_state = str(data.get("state", ""))
        if not expected_state or not hmac.compare_digest(expected_state, state):
            raise InvalidRequestError(
                "This sign-in attempt does not match. Start again.", reason="state_mismatch"
            )
        try:
            identity = google.exchange_code(
                code=code, code_verifier=str(data["verifier"]), nonce=str(data["nonce"])
            )
        except IdentityRejectedError as exc:
            self._audit("sign_in_refused", detail=f"google:{exc.reason}")
            raise
        result = self._sign_in(identity.email, identity.name, SignInMethod.GOOGLE)
        return replace(result, next_path=safe_next_path(str(data.get("next", ""))))

    # Email code ------------------------------------------------------------------------

    def request_email_code(self, email: str) -> EmailCodeSent:
        address = self._config.normalise_email(email)
        self._email_codes.send_code(address)
        return EmailCodeSent(
            expires_in=self._email_codes.code_ttl_seconds,
            resend_after=self._email_codes.resend_after_seconds,
        )

    def finish_email_code(self, *, email: str, code: str) -> SignInResult:
        address = self._config.normalise_email(email)
        self._email_codes.check_code(address, code)
        return self._sign_in(address, None, SignInMethod.EMAIL_CODE)

    # Session ---------------------------------------------------------------------------

    def refresh(self, refresh_token: str) -> SignInResult:
        try:
            record = self._tokens.check_refresh(refresh_token)
        except RefreshTokenReuseError as exc:
            self._audit("refresh_token_reuse", user_id=exc.user_id, detail="family revoked")
            raise
        user = self._store.users.get(record.user_id)
        if user is None or not user.is_active:
            self._tokens.revoke_family(record.family_id, USER_DEACTIVATED)
            raise InvalidTokenError()
        issued = self._tokens.rotate(record)
        return self._result(user, issued.token, issued.expires_at)

    def sign_out(self, refresh_token: str) -> None:
        record = self._tokens.end_session(refresh_token)
        if record is not None:
            self._audit("sign_out", user_id=record.user_id)

    def principal(self, access_token: str) -> Principal:
        return self._tokens.verify_access_token(access_token)

    def current_user(self, principal: Principal) -> User:
        user = self._store.users.get(principal.user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError()
        return user

    # Own account ---------------------------------------------------------------------

    def update_profile(
        self, principal: Principal, *, name: str | None = None, phone: str | None = None
    ) -> User:
        """Change your own display name and phone (None leaves a field unchanged)."""
        user = self.current_user(principal)
        updated = replace(
            user,
            name=clean_name(name) if name is not None else user.name,
            phone=clean_phone(phone) if phone is not None else user.phone,
        )
        if updated != user:
            self._store.users.update(updated)
            self._audit("profile_updated", user_id=user.user_id, actor_id=user.user_id)
        return updated

    def set_avatar(self, principal: Principal, data: bytes) -> User:
        """Store your profile photo (PNG, JPEG or WebP, at most 2 MB)."""
        user = self.current_user(principal)
        content_type = image_type(data)
        now = self._clock()
        self._store.avatars.put(
            user.user_id, Avatar(content_type=content_type, data=data, updated_at=now)
        )
        updated = replace(user, avatar_updated_at=now)
        self._store.users.update(updated)
        return updated

    def remove_avatar(self, principal: Principal) -> User:
        user = self.current_user(principal)
        self._store.avatars.delete(user.user_id)
        updated = replace(user, avatar_updated_at=None)
        self._store.users.update(updated)
        return updated

    def avatar(self, principal: Principal) -> Avatar:
        user = self.current_user(principal)
        avatar = self._store.avatars.get(user.user_id)
        if avatar is None:
            raise NotFoundError("No profile photo.")
        return avatar

    def request_email_change(self, principal: Principal, new_email: str) -> EmailCodeSent:
        """Send a code to the new address; the change happens only when it is confirmed."""
        user = self.current_user(principal)
        address = self._config.normalise_email(new_email)
        self._check_email_free(user, address)
        self._email_codes.send_code(address)
        return EmailCodeSent(
            expires_in=self._email_codes.code_ttl_seconds,
            resend_after=self._email_codes.resend_after_seconds,
        )

    def confirm_email_change(self, principal: Principal, *, new_email: str, code: str) -> User:
        """Switch to the new address once its code is right (proves the user owns it)."""
        user = self.current_user(principal)
        address = self._config.normalise_email(new_email)
        self._check_email_free(user, address)
        self._email_codes.check_code(address, code)
        updated = replace(user, email=address)
        self._store.users.update(updated)
        self._audit("email_changed", user_id=user.user_id, actor_id=user.user_id)
        return updated

    def _check_email_free(self, user: User, address: str) -> None:
        if address == user.email:
            raise ConflictError("That is already your email address.")
        owner = self._store.users.get_by_email(address)
        if owner is not None and owner.user_id != user.user_id:
            raise ConflictError("Another account already uses that email address.")

    # Administration --------------------------------------------------------------------

    def list_users(self) -> list[User]:
        return self._store.users.list_all()

    def recent_events(self, limit: int = 100) -> list[AuthEvent]:
        return self._store.audit.recent(limit)

    def update_user(
        self,
        actor: Principal,
        user_id: str,
        *,
        role: Role | None = None,
        status: UserStatus | None = None,
    ) -> User:
        """Change a user's role or status.

        The actor's role is re-read from the store, so a demoted administrator's unexpired
        access token cannot change anyone. Administrators cannot demote or deactivate
        themselves, so the acting administrator always remains: at least one active
        administrator exists after every change.
        """
        current_actor = self._store.users.get(actor.user_id)
        if current_actor is None or not current_actor.is_active:
            raise InvalidTokenError()
        if Permission.USERS_MANAGE not in current_actor.permissions:
            raise PermissionDeniedError("Your role does not allow this.", reason="users:manage")
        user = self._store.users.get(user_id)
        if user is None:
            raise NotFoundError("No such user.")
        updated = replace(user, role=role or user.role, status=status or user.status)
        if updated == user:
            return user
        stays_admin = updated.role is Role.ADMIN and updated.is_active
        if user.user_id == current_actor.user_id and not stays_admin:
            raise ConflictError(
                "You cannot remove your own administrator access. Ask another administrator."
            )
        self._store.users.update(updated)
        if updated.role is not user.role:
            self._audit(
                "role_changed",
                user_id=user.user_id,
                actor_id=current_actor.user_id,
                detail=f"{user.role.value}->{updated.role.value}",
            )
        if updated.status is not user.status:
            self._audit(
                "status_changed",
                user_id=user.user_id,
                actor_id=current_actor.user_id,
                detail=f"{user.status.value}->{updated.status.value}",
            )
            if not updated.is_active:
                self._tokens.revoke_user(user.user_id, USER_DEACTIVATED)
        return updated

    # Internals -------------------------------------------------------------------------

    def _require_google(self) -> GoogleOAuthClient:
        if self._google is None:
            raise MethodUnavailableError("Sign-in with Google is not available yet.")
        return self._google

    def _sign_in(self, email: str, name: str | None, method: SignInMethod) -> SignInResult:
        address = self._config.normalise_email(email)
        now = self._clock()
        bootstrap_admin = address in self._config.bootstrap_admins
        user = self._store.users.get_by_email(address)
        if user is None:
            user = User(
                user_id=uuid.uuid4().hex,
                email=address,
                name=name,
                role=Role.ADMIN if bootstrap_admin else DEFAULT_ROLE,
                status=UserStatus.ACTIVE,
                created_at=now,
                last_sign_in_at=now,
            )
            self._store.users.add(user)
            self._audit("user_registered", user_id=user.user_id, detail=method.value)
        else:
            if not user.is_active:
                self._audit("sign_in_refused", user_id=user.user_id, detail="deactivated")
                raise AccountDeactivatedError(
                    "Your account has been deactivated. Contact an administrator."
                )
            user = replace(
                user,
                name=user.name or name,
                role=Role.ADMIN if bootstrap_admin else user.role,
                last_sign_in_at=now,
            )
            self._store.users.update(user)
        self._audit("sign_in", user_id=user.user_id, detail=method.value)
        issued = self._tokens.start_session(user.user_id)
        return self._result(user, issued.token, issued.expires_at)

    def _result(self, user: User, refresh_token: str, refresh_expires_at: datetime) -> SignInResult:
        now = self._clock()
        return SignInResult(
            user=user,
            access_token=self._tokens.access_token(user),
            access_expires_in=self._tokens.access_ttl_seconds,
            refresh_token=refresh_token,
            refresh_expires_in=max(0, int((refresh_expires_at - now).total_seconds())),
        )

    def _audit(
        self,
        kind: str,
        *,
        user_id: str | None = None,
        actor_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        self._store.audit.record(
            AuthEvent(
                kind=kind,
                occurred_at=self._clock(),
                user_id=user_id,
                actor_id=actor_id,
                detail=detail,
            )
        )
