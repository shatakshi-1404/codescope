import pytest

from app.core.errors import RepositoryCloneError, RepositoryNotFoundError
from tests.helpers import add_repo, create_project, error_code

FETCH = "app.services.repository_service.fetch_default_branch"


def _raising(exc):
    def raiser(url):
        raise exc

    return raiser


def test_adding_a_repository_normalizes_the_url(client, team):
    r = client.post(
        f"/api/projects/{team.pid}/repositories",
        json={"url": "https://github.com/Acme/API.git"},
        headers=team.alice.headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["url"] == "https://github.com/acme/api"
    assert body["name"] == "Acme/API"
    assert body["default_branch"] == "main"
    assert body["latest_analysis"] is None


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 201), ("dave", 201), ("carol", 403), ("bob", 403), ("eve", 404)],
)
def test_who_can_add_repositories(client, team, who, expected):
    r = client.post(
        f"/api/projects/{team.pid}/repositories",
        json={"url": "https://github.com/acme/api"},
        headers=getattr(team, who).headers,
    )
    assert r.status_code == expected


@pytest.mark.parametrize("url", ["https://github.com/ACME/API.git", "github.com/acme/api/", "https://www.github.com/acme/api/tree/main"])
def test_duplicates_are_detected_whatever_the_spelling(client, team, url):
    add_repo(client, team.alice, team.pid, "https://github.com/acme/api")
    r = client.post(f"/api/projects/{team.pid}/repositories", json={"url": url}, headers=team.alice.headers)
    assert r.status_code == 409
    assert error_code(r) == "conflict"


def test_the_same_repository_can_live_in_two_projects(client, team):
    add_repo(client, team.alice, team.pid)
    other = create_project(client, team.eve, "Eve's project")
    add_repo(client, team.eve, other["id"])


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/acme/api",
        "git@github.com:acme/api.git",
        "ssh://git@github.com/acme/api",
        "https://user:pw@github.com/acme/api",
        "https://github.com.evil.com/acme/api",
        "not a url",
    ],
)
def test_invalid_urls_are_rejected_before_touching_the_network(client, team, monkeypatch, url):
    def never_called(_url):
        raise AssertionError("the network must not be contacted for an invalid URL")

    monkeypatch.setattr(FETCH, never_called)
    r = client.post(f"/api/projects/{team.pid}/repositories", json={"url": url}, headers=team.alice.headers)
    assert r.status_code == 422
    assert error_code(r) == "invalid_repository_url"


def test_empty_url_fails_validation(client, team):
    r = client.post(f"/api/projects/{team.pid}/repositories", json={"url": ""}, headers=team.alice.headers)
    assert r.status_code == 422


def test_missing_or_private_repository_is_a_404(client, team, monkeypatch):
    monkeypatch.setattr(FETCH, _raising(RepositoryNotFoundError("Repository not found, or it is private.")))
    r = client.post(f"/api/projects/{team.pid}/repositories", json={"url": "https://github.com/acme/ghost"}, headers=team.alice.headers)
    assert r.status_code == 404
    assert error_code(r) == "repository_not_found"
    assert client.get(f"/api/projects/{team.pid}/repositories", headers=team.alice.headers).json() == []


def test_a_git_failure_is_reported_as_a_502(client, team, monkeypatch):
    monkeypatch.setattr(FETCH, _raising(RepositoryCloneError("Could not download the repository.")))
    r = client.post(f"/api/projects/{team.pid}/repositories", json={"url": "https://github.com/acme/api"}, headers=team.alice.headers)
    assert r.status_code == 502
    assert error_code(r) == "repository_clone_failed"


def test_repository_list_visibility(client, team):
    add_repo(client, team.alice, team.pid)
    viewer = client.get(f"/api/projects/{team.pid}/repositories", headers=team.bob.headers)
    assert viewer.status_code == 200 and len(viewer.json()) == 1
    assert client.get(f"/api/projects/{team.pid}/repositories", headers=team.eve.headers).status_code == 404
