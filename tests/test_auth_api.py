"""The authentication and administration routes over HTTP (ADR-010).

Uses the real app with an injected service, so the research routes and the auth routes are
tested together: RBAC status codes, response headers and bodies.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.auth.errors import AuthNotConfiguredError
from ihub.auth.service import AuthService
from tests.auth_helpers import ADMIN, STAFF, Harness, make_harness


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


@pytest.fixture
def client(h: Harness, insights_db: Path) -> TestClient:
    return TestClient(create_app(lambda: insights_db, auth_service=lambda: h.service))


def sign_in(client: TestClient, h: Harness, address: str) -> dict:
    assert client.post("/api/auth/email/request", json={"email": address}).status_code == 202
    response = client.post(
        "/api/auth/email/verify", json={"email": address, "code": h.email.last_code}
    )
    assert response.status_code == 200, response.text
    h.clock.advance(seconds=31)
    return response.json()


def bearer(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_methods_tell_the_sign_in_screen_what_to_offer(client: TestClient) -> None:
    body = client.get("/api/auth/methods").json()
    assert body == {"google": True, "email_code": True, "allowed_domain": "unza.ac.zm"}


def test_email_sign_in_returns_a_token_pair_that_is_never_cached(
    client: TestClient, h: Harness
) -> None:
    client.post("/api/auth/email/request", json={"email": STAFF})
    response = client.post(
        "/api/auth/email/verify", json={"email": STAFF, "code": h.email.last_code}
    )
    body = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["next"] == "/overview"
    assert body["user"]["email"] == STAFF
    assert body["user"]["permissions"] == ["research:read"]


def test_me_needs_a_valid_bearer_token(client: TestClient, h: Harness) -> None:
    missing = client.get("/api/auth/me")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    junk = client.get("/api/auth/me", headers={"Authorization": "Bearer junk"})
    assert junk.status_code == 401
    assert 'error="invalid_token"' in junk.headers["www-authenticate"]

    tokens = sign_in(client, h, STAFF)
    me = client.get("/api/auth/me", headers=bearer(tokens)).json()
    assert (me["email"], me["role"], me["status"]) == (STAFF, "member", "active")


def test_refresh_rotates_and_sign_out_ends_the_session(client: TestClient, h: Harness) -> None:
    tokens = sign_in(client, h, STAFF)
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new = refreshed.json()
    assert new["refresh_token"] != tokens["refresh_token"]

    signed_out = client.post("/api/auth/sign-out", json={"refresh_token": new["refresh_token"]})
    assert signed_out.status_code == 204
    again = client.post("/api/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert again.status_code == 401


def test_rbac_members_cannot_reach_administration(client: TestClient, h: Harness) -> None:
    member = sign_in(client, h, STAFF)
    for method, path in (
        ("get", "/api/admin/users"),
        ("get", "/api/admin/roles"),
        ("get", "/api/admin/audit"),
        ("patch", f"/api/admin/users/{member['user']['id']}"),
    ):
        kwargs = {"json": {"role": "admin"}} if method == "patch" else {}
        response = getattr(client, method)(path, headers=bearer(member), **kwargs)
        assert response.status_code == 403, path
    assert client.get("/api/admin/users").status_code == 401


def test_a_demoted_admin_token_stops_working_for_administration(
    client: TestClient, h: Harness
) -> None:
    admin = sign_in(client, h, ADMIN)
    staff = sign_in(client, h, STAFF)
    staff_path = f"/api/admin/users/{staff['user']['id']}"
    client.patch(staff_path, headers=bearer(admin), json={"role": "admin"})
    staff = client.post("/api/auth/refresh", json={"refresh_token": staff["refresh_token"]}).json()
    assert staff["user"]["role"] == "admin"
    assert client.get("/api/admin/users", headers=bearer(staff)).status_code == 200

    client.patch(staff_path, headers=bearer(admin), json={"role": "member"})
    # The access token still claims "admin", but administration checks the store.
    assert client.get("/api/admin/users", headers=bearer(staff)).status_code == 403


def test_administrators_manage_users(client: TestClient, h: Harness) -> None:
    admin = sign_in(client, h, ADMIN)
    member = sign_in(client, h, STAFF)

    users = client.get("/api/admin/users", headers=bearer(admin)).json()
    assert [(user["email"], user["role"]) for user in users] == [
        (ADMIN, "admin"),
        (STAFF, "member"),
    ]
    promoted = client.patch(
        f"/api/admin/users/{member['user']['id']}",
        headers=bearer(admin),
        json={"role": "analyst"},
    )
    assert promoted.status_code == 200
    assert "research:export" in promoted.json()["permissions"]

    roles = client.get("/api/admin/roles", headers=bearer(admin)).json()
    assert {row["role"] for row in roles} == {
        "member",
        "analyst",
        "librarian",
        "unit-head",
        "executive",
        "admin",
    }
    audit = client.get("/api/admin/audit", headers=bearer(admin), params={"limit": 1}).json()
    assert audit[0]["kind"] == "role_changed"


def test_admin_changes_are_validated(client: TestClient, h: Harness) -> None:
    admin = sign_in(client, h, ADMIN)
    own = f"/api/admin/users/{admin['user']['id']}"
    demote = client.patch(own, headers=bearer(admin), json={"role": "member"})
    assert demote.status_code == 409
    invalid = client.patch(own, headers=bearer(admin), json={"role": "superuser"})
    assert invalid.status_code == 422
    missing = client.patch(
        "/api/admin/users/nobody", headers=bearer(admin), json={"role": "member"}
    )
    assert missing.status_code == 404


def test_bad_email_requests(client: TestClient) -> None:
    other = client.post("/api/auth/email/request", json={"email": "someone@gmail.com"})
    assert other.status_code == 400
    assert "@unza.ac.zm" in other.json()["detail"]
    assert client.post("/api/auth/email/request", json={"email": STAFF}).status_code == 202
    limited = client.post("/api/auth/email/request", json={"email": STAFF})
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_google_start_returns_the_flow_to_keep(client: TestClient) -> None:
    response = client.post("/api/auth/google/start", json={"next": "/topics"})
    body = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert body["authorization_url"].startswith("https://accounts.google.com/")
    assert body["flow_expires_in"] == 600 and body["flow"].count(".") == 2


def test_without_auth_configured_research_still_works(insights_db: Path) -> None:
    def not_configured() -> AuthService:
        raise AuthNotConfiguredError("Sign-in is not available: IHUB_AUTH_SECRET is not set.")

    client = TestClient(create_app(lambda: insights_db, auth_service=not_configured))
    assert client.get("/api/overview").status_code == 200
    response = client.get("/api/auth/methods")
    assert response.status_code == 503
    assert "IHUB_AUTH_SECRET" in response.json()["detail"]
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer x"}).status_code == 503


def test_require_admits_only_roles_with_the_permission(h: Harness, insights_db: Path) -> None:
    from typing import Annotated

    from fastapi import Depends

    from ihub.auth.api import require
    from ihub.auth.models import Principal
    from ihub.auth.rbac import Permission

    app = create_app(lambda: insights_db, auth_service=lambda: h.service)

    @app.get("/api/test/export")
    def export(
        principal: Annotated[Principal, Depends(require(Permission.RESEARCH_EXPORT))],
    ) -> dict[str, str]:
        return {"role": principal.role.value}

    client = TestClient(app)
    admin = sign_in(client, h, ADMIN)
    member = sign_in(client, h, STAFF)
    assert client.get("/api/test/export").status_code == 401
    assert client.get("/api/test/export", headers=bearer(member)).status_code == 403
    client.patch(
        f"/api/admin/users/{member['user']['id']}", headers=bearer(admin), json={"role": "analyst"}
    )
    analyst = client.post("/api/auth/refresh", json={"refresh_token": member["refresh_token"]})
    response = client.get("/api/test/export", headers=bearer(analyst.json()))
    assert response.status_code == 200
    assert response.json() == {"role": "analyst"}
