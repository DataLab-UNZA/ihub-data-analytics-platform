"""Your own account: name, phone, profile photo and a verified email change."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.auth.errors import ConflictError, InvalidCodeError, InvalidEmailError, InvalidRequestError
from ihub.auth.profile import MAX_AVATAR_BYTES, clean_name, clean_phone, image_type
from ihub.auth.sqlite_store import SqliteAuthStore
from tests.auth_helpers import ADMIN, STAFF, Harness, make_harness

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


def signed_in(h: Harness, address: str = STAFF):
    return h.service.principal(h.sign_in_by_email(address).access_token)


# Rules -------------------------------------------------------------------------------------


def test_names_are_trimmed_and_limited() -> None:
    assert clean_name("  Test   Staff ") == "Test Staff"
    assert clean_name("   ") is None
    with pytest.raises(InvalidRequestError):
        clean_name("x" * 101)


@pytest.mark.parametrize("phone", ["+260 97 123 4567", "0971234567", "(021) 129-1234"])
def test_reasonable_phone_numbers_are_kept(phone: str) -> None:
    assert clean_phone(phone) == phone


@pytest.mark.parametrize("phone", ["12345", "+260 97 123 4567 890 12", "call me", "097<script>"])
def test_odd_phone_numbers_are_refused(phone: str) -> None:
    with pytest.raises(InvalidRequestError, match="7 to 15 digits"):
        clean_phone(phone)


def test_photo_type_comes_from_the_bytes_not_the_label() -> None:
    assert image_type(PNG) == "image/png"
    assert image_type(JPEG) == "image/jpeg"
    assert image_type(WEBP) == "image/webp"
    for not_an_image in (b"<svg onload=alert(1)>", b"GIF89a....", b"%PDF-1.7", b""):
        with pytest.raises(InvalidRequestError, match="PNG, JPEG or WebP"):
            image_type(not_an_image)
    with pytest.raises(InvalidRequestError, match="2 MB"):
        image_type(PNG + b"\x00" * MAX_AVATAR_BYTES)


# Service -----------------------------------------------------------------------------------


def test_profile_changes_are_saved(h: Harness) -> None:
    me = signed_in(h)
    user = h.service.update_profile(me, name=" Test  Staff ", phone="+260 97 123 4567")
    assert (user.name, user.phone) == ("Test Staff", "+260 97 123 4567")
    assert h.service.update_profile(me, name=None).phone == "+260 97 123 4567"  # None: unchanged
    assert h.service.update_profile(me, phone="").phone is None  # empty: cleared


def test_photos_are_stored_replaced_and_removed(h: Harness) -> None:
    me = signed_in(h)
    assert h.service.set_avatar(me, PNG).avatar_updated_at is not None
    h.service.set_avatar(me, JPEG)
    avatar = h.service.avatar(me)
    assert (avatar.content_type, avatar.data) == ("image/jpeg", JPEG)
    assert h.service.remove_avatar(me).avatar_updated_at is None
    with pytest.raises(Exception, match="No profile photo"):
        h.service.avatar(me)


def test_email_changes_only_after_the_new_address_is_confirmed(h: Harness) -> None:
    me = signed_in(h)
    new = "new.address@unza.ac.zm"
    h.service.request_email_change(me, new)
    to, code = h.email.sent[-1]
    assert to == new  # the code goes to the NEW address
    assert h.store.users.get(me.user_id).email == STAFF  # nothing changed yet
    with pytest.raises(InvalidCodeError):
        h.service.confirm_email_change(
            me, new_email=new, code="000000" if code != "000000" else "1"
        )
    assert h.service.confirm_email_change(me, new_email=new, code=code).email == new
    h.clock.advance(seconds=31)
    assert h.sign_in_by_email(new).user.user_id == me.user_id  # same account, new address


def test_email_change_rules(h: Harness) -> None:
    me = signed_in(h)
    signed_in(h, ADMIN)
    with pytest.raises(ConflictError, match="already uses"):
        h.service.request_email_change(me, ADMIN)
    with pytest.raises(ConflictError, match="already your"):
        h.service.request_email_change(me, STAFF)
    with pytest.raises(InvalidEmailError):
        h.service.request_email_change(me, "someone@gmail.com")  # the domain rule still applies


def test_old_stores_gain_the_new_columns(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as con:
        con.execute(
            "CREATE TABLE users (user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT, "
            "role TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, "
            "last_sign_in_at TEXT)"
        )
        con.execute(
            "INSERT INTO users VALUES ('u1','a@unza.ac.zm',NULL,'member','active',"
            "'2026-11-01T00:00:00.000000+00:00',NULL)"
        )
    user = SqliteAuthStore(path).users.get("u1")
    assert user is not None and user.phone is None and user.avatar_updated_at is None


# HTTP --------------------------------------------------------------------------------------


@pytest.fixture
def client(h: Harness, insights_db: Path) -> TestClient:
    test_client = TestClient(create_app(lambda: insights_db, auth_service=lambda: h.service))
    test_client.headers["Authorization"] = f"Bearer {h.sign_in_by_email().access_token}"
    return test_client


def test_account_routes_over_http(client: TestClient, h: Harness) -> None:
    me = client.patch("/api/auth/me", json={"name": "Test Staff", "phone": "+260 97 123 4567"})
    assert me.status_code == 200 and me.json()["phone"] == "+260 97 123 4567"
    assert client.patch("/api/auth/me", json={"phone": "nope"}).status_code == 400

    assert client.get("/api/auth/me/avatar").status_code == 404
    uploaded = client.put("/api/auth/me/avatar", content=PNG, headers={"Content-Type": "image/png"})
    assert uploaded.status_code == 200 and uploaded.json()["avatar_updated_at"]
    photo = client.get("/api/auth/me/avatar")
    assert photo.content == PNG and photo.headers["content-type"] == "image/png"
    assert photo.headers["x-content-type-options"] == "nosniff"
    disguised = client.put(
        "/api/auth/me/avatar", content=b"<svg/>", headers={"Content-Type": "image/png"}
    )
    assert disguised.status_code == 400
    too_big = client.put("/api/auth/me/avatar", content=PNG + b"\x00" * MAX_AVATAR_BYTES)
    assert too_big.status_code == 400
    assert client.delete("/api/auth/me/avatar").json()["avatar_updated_at"] is None

    new = "new.address@unza.ac.zm"
    assert client.post("/api/auth/me/email/request", json={"email": new}).status_code == 202
    changed = client.post(
        "/api/auth/me/email/verify", json={"email": new, "code": h.email.last_code}
    )
    assert changed.status_code == 200 and changed.json()["email"] == new


def test_account_routes_need_sign_in(h: Harness, insights_db: Path) -> None:
    anonymous = TestClient(create_app(lambda: insights_db, auth_service=lambda: h.service))
    assert anonymous.patch("/api/auth/me", json={"name": "x"}).status_code == 401
    assert anonymous.put("/api/auth/me/avatar", content=PNG).status_code == 401
    assert anonymous.get("/api/auth/me/avatar").status_code == 401
    assert anonymous.post("/api/auth/me/email/request", json={"email": STAFF}).status_code == 401
