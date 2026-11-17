"""Saved charts and dashboards: permissions, ownership, visibility and validation."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.auth.errors import InvalidRequestError, NotFoundError, PermissionDeniedError
from ihub.auth.rbac import Role
from ihub.workspace.service import WorkspaceService
from ihub.workspace.sqlite_store import SqliteWorkspaceStore
from tests.auth_helpers import ADMIN, STAFF, Harness, make_harness

ANALYST = "test.analyst@unza.ac.zm"
QUERY = {"dataset": "publications", "metrics": ["count"], "groupby": ["year"]}


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return make_harness(tmp_path)


@pytest.fixture
def ws(tmp_path: Path) -> WorkspaceService:
    return WorkspaceService(SqliteWorkspaceStore(tmp_path / "workspace.sqlite"))


def people(h: Harness):
    admin = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    member = h.service.principal(h.sign_in_by_email(STAFF).access_token)
    analyst_id = h.service.principal(h.sign_in_by_email(ANALYST).access_token).user_id
    h.service.update_user(admin, analyst_id, role=Role.ANALYST)
    analyst = h.service.principal(
        h.service.refresh(h.sign_in_by_email(ANALYST).refresh_token).access_token
    )
    return admin, analyst, member


def test_who_may_save_and_change_charts(h: Harness, ws: WorkspaceService) -> None:
    admin, analyst, member = people(h)
    with pytest.raises(PermissionDeniedError):
        ws.create_chart(member, name="Mine", viz_type="bar", params=QUERY, options={})
    chart = ws.create_chart(
        analyst, name=" Output  by year ", viz_type="bar", params=QUERY, options={"legend": True}
    )
    assert (chart.name, chart.dataset) == ("Output by year", "publications")
    with pytest.raises(PermissionDeniedError):
        ws.update_chart(member, chart.chart_id, name="Hijacked")
    assert ws.update_chart(analyst, chart.chart_id, viz_type="line").viz_type == "line"
    assert ws.update_chart(admin, chart.chart_id, name="Checked").name == "Checked"  # admins may
    assert [c.chart_id for c in ws.list_charts()] == [chart.chart_id]


@pytest.mark.parametrize(
    ("viz_type", "params"),
    [
        ("bar", {"dataset": "publications", "groupby": ["nope"], "metrics": ["count"]}),
        ("bar", {"dataset": "publications; DROP", "metrics": ["count"]}),
        ("bar", {"dataset": "publications"}),  # neither metric nor group-by
        ("rocket", QUERY),
    ],
)
def test_invalid_charts_are_refused(
    h: Harness, ws: WorkspaceService, viz_type: str, params: dict
) -> None:
    admin, _, _ = people(h)
    with pytest.raises(InvalidRequestError):
        ws.create_chart(admin, name="Bad", viz_type=viz_type, params=params, options={})


def test_dashboards_visibility_layout_and_favourites(h: Harness, ws: WorkspaceService) -> None:
    admin, analyst, member = people(h)
    chart = ws.create_chart(analyst, name="By year", viz_type="bar", params=QUERY, options={})
    board = ws.create_dashboard(analyst, title="Research output")
    assert ws.list_dashboards(member) == []  # drafts are private
    with pytest.raises(NotFoundError):
        ws.get_dashboard(member, board.dashboard_id)
    assert ws.list_dashboards(admin)  # administrators see drafts

    board = ws.update_dashboard(
        analyst,
        board.dashboard_id,
        published=True,
        items=[{"chart_id": chart.chart_id, "width": 99, "height": 1}],
        filters=[{"label": "Type", "column": "publication_type"}],
    )
    assert (board.items[0].width, board.items[0].height) == (12, 4)  # clamped to the grid
    assert board.filters[0].column == "publication_type"
    assert [d.dashboard_id for d in ws.list_dashboards(member)] == [board.dashboard_id]

    ws.set_favourite(member, board.dashboard_id, True)
    assert member.user_id in ws.get_dashboard(member, board.dashboard_id).favourited_by
    with pytest.raises(PermissionDeniedError):
        ws.update_dashboard(member, board.dashboard_id, title="Mine now")
    with pytest.raises(InvalidRequestError):
        ws.update_dashboard(analyst, board.dashboard_id, filters=[{"column": "secret"}])

    ws.delete_chart(analyst, chart.chart_id)
    assert ws.get_dashboard(analyst, board.dashboard_id).items == ()  # removed everywhere


@pytest.fixture
def clients(h: Harness, insights_db: Path, tmp_path: Path):
    service = WorkspaceService(SqliteWorkspaceStore(tmp_path / "ws.sqlite"))
    app = create_app(
        lambda: insights_db,
        auth_service=lambda: h.service,
        require_sign_in=True,
        workspace_service=lambda: service,
    )
    admin, member = TestClient(app), TestClient(app)
    admin.headers["Authorization"] = f"Bearer {h.sign_in_by_email(ADMIN).access_token}"
    member.headers["Authorization"] = f"Bearer {h.sign_in_by_email(STAFF).access_token}"
    return admin, member, TestClient(app)


def test_workspace_api(clients) -> None:
    admin, member, anonymous = clients
    assert anonymous.get("/api/charts").status_code == 401
    body = {"name": "By year", "viz_type": "bar", "params": QUERY}
    assert member.post("/api/charts", json=body).status_code == 403
    chart = admin.post("/api/charts", json=body)
    assert chart.status_code == 201 and chart.json()["can_edit"] is True
    chart_id = chart.json()["chart_id"]
    assert member.get(f"/api/charts/{chart_id}").json()["can_edit"] is False
    assert member.patch(f"/api/charts/{chart_id}", json={"name": "x"}).status_code == 403
    assert admin.post("/api/charts", json={**body, "params": {"dataset": "x"}}).status_code == 400

    board = admin.post("/api/dashboards", json={"title": "Overview"}).json()
    board_id = board["dashboard_id"]
    assert member.get(f"/api/dashboards/{board_id}").status_code == 404  # draft
    patched = admin.patch(
        f"/api/dashboards/{board_id}",
        json={"published": True, "items": [{"chart_id": chart_id, "width": 6, "height": 8}]},
    ).json()
    assert patched["published"] and patched["items"][0]["chart_id"] == chart_id
    fav = member.put(f"/api/dashboards/{board_id}/favourite", json={"favourite": True}).json()
    assert fav["favourite"] is True and fav["favourite_count"] == 1
    assert "favourited_by" not in fav  # who favourited stays private
    assert admin.get(f"/api/dashboards/{board_id}").json()["favourite"] is False
    assert member.delete(f"/api/dashboards/{board_id}").status_code == 403
    assert admin.delete(f"/api/dashboards/{board_id}").status_code == 204
