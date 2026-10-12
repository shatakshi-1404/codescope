import pytest
from sqlalchemy import func, select

from app.models import ProjectMember
from tests.helpers import add_member, create_project, error_code, member_row_id, register

# alice = OWNER, dave = ADMIN, carol = MEMBER, bob = VIEWER, eve = stranger


# ------------------------------------------------------------ authentication
UNAUTHENTICATED = [
    ("GET", "/api/projects"),
    ("POST", "/api/projects"),
    ("GET", "/api/projects/1"),
    ("PATCH", "/api/projects/1"),
    ("DELETE", "/api/projects/1"),
    ("GET", "/api/projects/1/members"),
    ("POST", "/api/projects/1/repositories"),
    ("GET", "/api/projects/1/activity"),
    ("GET", "/api/projects/1/issues"),
    ("POST", "/api/repositories/1/analyze"),
    ("GET", "/api/analyses/1"),
    ("GET", "/api/analyses/1/report"),
    ("PATCH", "/api/issues/1/status"),
    ("GET", "/api/dashboard"),
    ("GET", "/api/activity"),
]


@pytest.mark.parametrize("method, path", UNAUTHENTICATED)
def test_every_protected_endpoint_requires_a_token(client, method, path):
    body = {"name": "x", "url": "https://github.com/a/b", "status": "OPEN"}
    r = client.request(method, path, json=body if method in ("POST", "PATCH") else None)
    assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


# ------------------------------------------------------------------ projects
def test_creator_becomes_owner(client):
    alice = register(client)
    r = client.post("/api/projects", json={"name": "Payments", "description": "API"}, headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["my_role"] == "OWNER"
    assert r.json()["owner_id"] == alice.id


def test_blank_project_name_is_rejected(client):
    alice = register(client)
    assert client.post("/api/projects", json={"name": "   "}, headers=alice.headers).status_code == 422


def test_project_list_only_contains_my_projects(client, team):
    from tests.helpers import create_project as mk

    mk(client, team.eve, "Eve's project")
    mine = lambda who: [p["name"] for p in client.get("/api/projects", headers=who.headers).json()]  # noqa: E731
    assert mine(team.alice) == ["Acme API"]
    assert mine(team.carol) == ["Acme API"]
    assert mine(team.eve) == ["Eve's project"]


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 200), ("dave", 200), ("carol", 200), ("bob", 200), ("eve", 404)],
)
def test_who_can_view_a_project(client, team, who, expected):
    r = client.get(f"/api/projects/{team.pid}", headers=getattr(team, who).headers)
    assert r.status_code == expected
    if expected == 404:
        assert error_code(r) == "not_found"


def test_the_role_is_reported_per_caller(client, team):
    role = lambda who: client.get(f"/api/projects/{team.pid}", headers=who.headers).json()["my_role"]  # noqa: E731
    assert [role(team.alice), role(team.dave), role(team.carol), role(team.bob)] == [
        "OWNER", "ADMIN", "MEMBER", "VIEWER",
    ]


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 200), ("dave", 200), ("carol", 403), ("bob", 403), ("eve", 404)],
)
def test_who_can_edit_a_project(client, team, who, expected):
    r = client.patch(f"/api/projects/{team.pid}", json={"name": "Renamed"}, headers=getattr(team, who).headers)
    assert r.status_code == expected


def test_partial_update_keeps_other_fields(client, team):
    r = client.patch(f"/api/projects/{team.pid}", json={"description": "New text"}, headers=team.alice.headers)
    assert r.json()["name"] == "Acme API"
    assert r.json()["description"] == "New text"
    assert client.patch(f"/api/projects/{team.pid}", json={"name": ""}, headers=team.alice.headers).status_code == 422


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 204), ("dave", 403), ("carol", 403), ("bob", 403), ("eve", 404)],
)
def test_who_can_delete_a_project(client, team, who, expected):
    r = client.delete(f"/api/projects/{team.pid}", headers=getattr(team, who).headers)
    assert r.status_code == expected


def test_deleting_a_project_removes_it_for_everyone(client, team, db):
    assert client.delete(f"/api/projects/{team.pid}", headers=team.alice.headers).status_code == 204
    assert client.get(f"/api/projects/{team.pid}", headers=team.alice.headers).status_code == 404
    assert client.get(f"/api/projects/{team.pid}", headers=team.carol.headers).status_code == 404
    assert db.scalar(select(func.count()).select_from(ProjectMember)) == 0


# ------------------------------------------------------------------- members
@pytest.mark.parametrize(
    "who, expected",
    [("alice", 200), ("dave", 200), ("carol", 200), ("bob", 200), ("eve", 404)],
)
def test_who_can_list_members(client, team, who, expected):
    r = client.get(f"/api/projects/{team.pid}/members", headers=getattr(team, who).headers)
    assert r.status_code == expected
    if expected == 200:
        assert {m["role"] for m in r.json()} == {"OWNER", "ADMIN", "MEMBER", "VIEWER"}


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 201), ("dave", 201), ("carol", 403), ("bob", 403), ("eve", 404)],
)
def test_who_can_invite_members(client, team, who, expected):
    frank = register(client, "Frank")
    r = client.post(
        f"/api/projects/{team.pid}/members",
        json={"email": frank.email, "role": "MEMBER"},
        headers=getattr(team, who).headers,
    )
    assert r.status_code == expected


def test_only_the_owner_can_create_admins(client, team):
    frank = register(client, "Frank")
    body = {"email": frank.email, "role": "ADMIN"}
    by_admin = client.post(f"/api/projects/{team.pid}/members", json=body, headers=team.dave.headers)
    assert by_admin.status_code == 403
    assert error_code(by_admin) == "forbidden"
    assert client.post(f"/api/projects/{team.pid}/members", json=body, headers=team.alice.headers).status_code == 201


def test_owner_role_cannot_be_assigned_by_invite(client, team):
    frank = register(client, "Frank")
    r = client.post(
        f"/api/projects/{team.pid}/members", json={"email": frank.email, "role": "OWNER"}, headers=team.alice.headers
    )
    assert r.status_code == 422
    assert error_code(r) == "business_rule_violation"


def test_cannot_invite_unknown_or_existing_users(client, team):
    url = f"/api/projects/{team.pid}/members"
    unknown = client.post(url, json={"email": "ghost@example.com", "role": "MEMBER"}, headers=team.alice.headers)
    assert unknown.status_code == 404
    duplicate = client.post(url, json={"email": team.carol.email, "role": "MEMBER"}, headers=team.alice.headers)
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 200), ("dave", 403), ("carol", 403), ("bob", 403), ("eve", 404)],
)
def test_who_can_change_roles(client, team, who, expected):
    row = member_row_id(client, team.alice, team.pid, team.carol.email)
    r = client.patch(
        f"/api/projects/{team.pid}/members/{row}", json={"role": "VIEWER"}, headers=getattr(team, who).headers
    )
    assert r.status_code == expected
    if expected == 200:
        assert r.json()["role"] == "VIEWER"


def test_a_member_cannot_promote_themselves(client, team):
    row = member_row_id(client, team.alice, team.pid, team.carol.email)
    r = client.patch(f"/api/projects/{team.pid}/members/{row}", json={"role": "ADMIN"}, headers=team.carol.headers)
    assert r.status_code == 403
    members = client.get(f"/api/projects/{team.pid}/members", headers=team.alice.headers).json()
    assert next(m for m in members if m["email"] == team.carol.email)["role"] == "MEMBER"


def test_the_owner_role_is_protected(client, team):
    owner_row = member_row_id(client, team.alice, team.pid, team.alice.email)
    carol_row = member_row_id(client, team.alice, team.pid, team.carol.email)

    assign = client.patch(f"/api/projects/{team.pid}/members/{carol_row}", json={"role": "OWNER"}, headers=team.alice.headers)
    assert assign.status_code == 422
    demote = client.patch(f"/api/projects/{team.pid}/members/{owner_row}", json={"role": "MEMBER"}, headers=team.alice.headers)
    assert demote.status_code == 422
    remove_self = client.delete(f"/api/projects/{team.pid}/members/{owner_row}", headers=team.alice.headers)
    assert remove_self.status_code == 422
    remove_by_admin = client.delete(f"/api/projects/{team.pid}/members/{owner_row}", headers=team.dave.headers)
    assert remove_by_admin.status_code == 422


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 204), ("dave", 204), ("carol", 403), ("bob", 403), ("eve", 404)],
)
def test_who_can_remove_members(client, team, who, expected):
    row = member_row_id(client, team.alice, team.pid, team.bob.email)
    r = client.delete(f"/api/projects/{team.pid}/members/{row}", headers=getattr(team, who).headers)
    assert r.status_code == expected


def test_admins_cannot_remove_other_admins(client, team):
    gina = register(client, "Gina")
    add_member(client, team.alice, team.pid, gina, "ADMIN")
    row = member_row_id(client, team.alice, team.pid, gina.email)
    assert client.delete(f"/api/projects/{team.pid}/members/{row}", headers=team.dave.headers).status_code == 403
    assert client.delete(f"/api/projects/{team.pid}/members/{row}", headers=team.alice.headers).status_code == 204


def test_a_removed_member_loses_access_immediately(client, team):
    row = member_row_id(client, team.alice, team.pid, team.carol.email)
    assert client.delete(f"/api/projects/{team.pid}/members/{row}", headers=team.alice.headers).status_code == 204
    assert client.get(f"/api/projects/{team.pid}", headers=team.carol.headers).status_code == 404


def test_member_ids_cannot_be_used_across_projects(client, team):
    """Eve OWNS project 2. She must not be able to touch members of project 1 by mixing ids."""
    eve_project = create_project(client, team.eve, "Eve's project")
    carol_row = member_row_id(client, team.alice, team.pid, team.carol.email)

    patch = client.patch(
        f"/api/projects/{eve_project['id']}/members/{carol_row}", json={"role": "VIEWER"}, headers=team.eve.headers
    )
    delete = client.delete(f"/api/projects/{eve_project['id']}/members/{carol_row}", headers=team.eve.headers)
    assert patch.status_code == 404
    assert delete.status_code == 404

    members = client.get(f"/api/projects/{team.pid}/members", headers=team.alice.headers).json()
    assert next(m for m in members if m["email"] == team.carol.email)["role"] == "MEMBER"
