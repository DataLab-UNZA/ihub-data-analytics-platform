"""Registration, bootstrap administrators, deactivation and the last-administrator rule."""

from pathlib import Path

import pytest

from ihub.auth.errors import (
    AccountDeactivatedError,
    ConflictError,
    InvalidTokenError,
    NotFoundError,
    PermissionDeniedError,
)
from ihub.auth.models import UserStatus
from ihub.auth.rbac import Permission, Role
from tests.auth_helpers import ADMIN, STAFF, Harness, make_harness


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


def test_bootstrap_addresses_become_administrators(h: Harness) -> None:
    admin = h.sign_in_by_email(ADMIN)
    assert admin.user.role is Role.ADMIN
    assert h.service.principal(admin.access_token).has(Permission.USERS_MANAGE)


def test_a_returning_user_keeps_their_account(h: Harness) -> None:
    first = h.sign_in_by_email(STAFF)
    again = h.sign_in_with_google()  # the same address through the other method
    assert again.user.user_id == first.user.user_id
    assert again.user.name == "Test Staff"  # filled in from Google
    assert len(h.store.users.list_all()) == 1


def test_role_changes_apply_at_the_next_refresh(h: Harness) -> None:
    admin = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    staff = h.sign_in_by_email(STAFF)
    h.service.update_user(admin, staff.user.user_id, role=Role.LIBRARIAN)
    refreshed = h.service.refresh(staff.refresh_token)
    principal = h.service.principal(refreshed.access_token)
    assert principal.role is Role.LIBRARIAN
    assert principal.has(Permission.QUALITY_REVIEW)
    event = h.store.audit.recent(1)[0]
    assert (event.kind, event.detail, event.actor_id) == (
        "role_changed",
        "member->librarian",
        admin.user_id,
    )


def test_deactivation_ends_sessions_and_blocks_sign_in(h: Harness) -> None:
    admin = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    staff = h.sign_in_by_email(STAFF)
    h.service.update_user(admin, staff.user.user_id, status=UserStatus.DEACTIVATED)
    with pytest.raises(InvalidTokenError):
        h.service.refresh(staff.refresh_token)
    with pytest.raises(AccountDeactivatedError):
        h.sign_in_by_email(STAFF)
    h.clock.advance(seconds=31)
    h.service.update_user(admin, staff.user.user_id, status=UserStatus.ACTIVE)
    h.sign_in_by_email(STAFF)


def test_administrators_cannot_remove_their_own_access(h: Harness) -> None:
    admin = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    with pytest.raises(ConflictError, match="your own"):
        h.service.update_user(admin, admin.user_id, role=Role.MEMBER)
    with pytest.raises(ConflictError, match="your own"):
        h.service.update_user(admin, admin.user_id, status=UserStatus.DEACTIVATED)


def test_a_demoted_administrator_loses_admin_rights_at_once(tmp_path: Path) -> None:
    h = make_harness(tmp_path, bootstrap_admins=frozenset({ADMIN, STAFF}))
    first = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    second_tokens = h.sign_in_by_email(STAFF)
    second = h.service.principal(second_tokens.access_token)
    h.service.update_user(first, second.user_id, role=Role.EXECUTIVE)
    # The second user's access token still says "admin" for up to 15 minutes, but
    # administration re-reads the role from the store.
    assert second.role is Role.ADMIN
    with pytest.raises(PermissionDeniedError):
        h.service.update_user(second, first.user_id, role=Role.MEMBER)
    assert h.store.users.get(first.user_id).role is Role.ADMIN


def test_bootstrap_administrators_are_restored_at_sign_in(tmp_path: Path) -> None:
    h = make_harness(tmp_path, bootstrap_admins=frozenset({ADMIN, STAFF}))
    first = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    second = h.sign_in_by_email(STAFF)
    h.service.update_user(first, second.user.user_id, role=Role.MEMBER)
    assert h.sign_in_by_email(STAFF).user.role is Role.ADMIN


def test_unknown_users_and_no_op_updates(h: Harness) -> None:
    admin = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    with pytest.raises(NotFoundError):
        h.service.update_user(admin, "no-such-user", role=Role.MEMBER)
    user = h.service.update_user(admin, admin.user_id)
    assert user.role is Role.ADMIN
