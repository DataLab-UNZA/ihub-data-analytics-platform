"""Role-based access control: the single table that maps roles to permissions (ADR-010).

Routes depend on a :class:`Permission`, never on a role name, so changing what a role may
do means changing ``ROLE_PERMISSIONS`` and nothing else.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class Permission(StrEnum):
    """Something a user may do."""

    RESEARCH_READ = "research:read"
    RESEARCH_EXPORT = "research:export"
    REPORTS_MANAGE = "reports:manage"
    QUALITY_REVIEW = "quality:review"
    SOURCES_MANAGE = "sources:manage"
    MEMBERS_READ = "members:read"  # named staff and their publications (ADR-014)
    USERS_MANAGE = "users:manage"


class Role(StrEnum):
    """A named set of permissions, assigned to each user by an administrator."""

    MEMBER = "member"
    ANALYST = "analyst"
    LIBRARIAN = "librarian"
    UNIT_HEAD = "unit-head"
    EXECUTIVE = "executive"
    ADMIN = "admin"


DEFAULT_ROLE = Role.MEMBER
"""The role a user gets at registration (their first sign-in)."""

_READ = frozenset({Permission.RESEARCH_READ})
_ANALYSE = _READ | {Permission.RESEARCH_EXPORT, Permission.REPORTS_MANAGE}
_LEADERSHIP = _ANALYSE | {Permission.MEMBERS_READ}

ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = MappingProxyType(
    {
        Role.MEMBER: _READ,
        Role.ANALYST: _ANALYSE,
        Role.LIBRARIAN: _READ | {Permission.RESEARCH_EXPORT, Permission.QUALITY_REVIEW},
        Role.UNIT_HEAD: _LEADERSHIP,
        Role.EXECUTIVE: _LEADERSHIP,
        Role.ADMIN: frozenset(Permission),
    }
)


def permissions_for(role: Role) -> frozenset[Permission]:
    """The permissions a role grants."""
    return ROLE_PERMISSIONS[role]
