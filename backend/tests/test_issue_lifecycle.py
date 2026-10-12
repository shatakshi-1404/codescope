import pytest

from tests.helpers import error_code, run_analysis


def _issues(client, who, analysis_id, query=""):
    r = client.get(f"/api/analyses/{analysis_id}/issues?limit=200{query}", headers=who.headers)
    assert r.status_code == 200, r.text
    return r.json()


def _issue(client, who, analysis_id, title):
    return next(i for i in _issues(client, who, analysis_id)["items"] if i["title"] == title)


def _set(client, who, issue_id, status):
    return client.patch(f"/api/issues/{issue_id}/status", json={"status": status}, headers=who.headers)


def _activity_actions(client, who, pid):
    r = client.get(f"/api/projects/{pid}/activity?limit=100", headers=who.headers)
    return [a["action"] for a in r.json()["items"]]


OS_IMPORT = "Unused import: os"
JSON_IMPORT = "Unused import: json"


def test_resolving_records_who_and_when(client, analyzed):
    issue = _issue(client, analyzed.alice, analyzed.analysis["id"], OS_IMPORT)
    assert issue["status"] == "OPEN" and issue["resolved_by"] is None

    r = _set(client, analyzed.carol, issue["id"], "RESOLVED")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "RESOLVED"
    assert body["resolved_by"] == analyzed.carol.id
    assert body["resolved_at"] is not None


def test_status_changes_are_idempotent_and_audited_once(client, analyzed):
    issue = _issue(client, analyzed.alice, analyzed.analysis["id"], OS_IMPORT)
    _set(client, analyzed.alice, issue["id"], "RESOLVED")
    _set(client, analyzed.alice, issue["id"], "RESOLVED")  # again: nothing new happens
    assert _activity_actions(client, analyzed.alice, analyzed.pid).count("issue_resolved") == 1


def test_reopening_clears_the_resolution(client, analyzed):
    issue = _issue(client, analyzed.alice, analyzed.analysis["id"], OS_IMPORT)
    _set(client, analyzed.alice, issue["id"], "RESOLVED")
    reopened = _set(client, analyzed.alice, issue["id"], "OPEN").json()
    assert reopened["status"] == "OPEN"
    assert reopened["resolved_by"] is None and reopened["resolved_at"] is None
    assert "issue_reopened" in _activity_actions(client, analyzed.alice, analyzed.pid)


def test_findings_are_never_deleted(client, analyzed):
    aid = analyzed.analysis["id"]
    total_before = _issues(client, analyzed.alice, aid)["total"]
    issue = _issue(client, analyzed.alice, aid, OS_IMPORT)

    _set(client, analyzed.alice, issue["id"], "RESOLVED")

    assert _issues(client, analyzed.alice, aid)["total"] == total_before
    resolved = _issues(client, analyzed.alice, aid, "&status=RESOLVED")
    assert [i["id"] for i in resolved["items"]] == [issue["id"]]
    assert _issues(client, analyzed.alice, aid, "&status=OPEN")["total"] == total_before - 1


@pytest.mark.parametrize(
    "who, expected",
    [("alice", 200), ("dave", 200), ("carol", 200), ("bob", 403), ("eve", 404)],
)
def test_who_can_triage_issues(client, analyzed, who, expected):
    issue = _issue(client, analyzed.alice, analyzed.analysis["id"], OS_IMPORT)
    r = _set(client, getattr(analyzed, who), issue["id"], "IGNORED")
    assert r.status_code == expected


def test_who_can_read_a_single_issue(client, analyzed):
    issue = _issue(client, analyzed.alice, analyzed.analysis["id"], OS_IMPORT)
    assert client.get(f"/api/issues/{issue['id']}", headers=analyzed.bob.headers).status_code == 200
    stranger = client.get(f"/api/issues/{issue['id']}", headers=analyzed.eve.headers)
    assert stranger.status_code == 404
    assert error_code(stranger) == "not_found"
    assert client.get("/api/issues/99999", headers=analyzed.alice.headers).status_code == 404
    assert _set(client, analyzed.alice, 99999, "RESOLVED").status_code == 404


def test_invalid_status_is_rejected(client, analyzed):
    issue = _issue(client, analyzed.alice, analyzed.analysis["id"], OS_IMPORT)
    r = _set(client, analyzed.alice, issue["id"], "DONE")
    assert r.status_code == 422
    assert error_code(r) == "validation_error"


def test_ignored_issues_stay_ignored_after_re_analysis_but_resolved_ones_reopen(client, analyzed):
    first = analyzed.analysis["id"]
    ignored = _issue(client, analyzed.alice, first, OS_IMPORT)
    resolved = _issue(client, analyzed.alice, first, JSON_IMPORT)
    _set(client, analyzed.alice, ignored["id"], "IGNORED")
    _set(client, analyzed.alice, resolved["id"], "RESOLVED")

    second = run_analysis(client, analyzed.alice, analyzed.repo["id"])["id"]
    assert second != first

    carried = _issue(client, analyzed.alice, second, OS_IMPORT)
    assert carried["status"] == "IGNORED"            # the decision "we accept this" survives
    assert carried["resolved_by"] == analyzed.alice.id
    reappeared = _issue(client, analyzed.alice, second, JSON_IMPORT)
    assert reappeared["status"] == "OPEN"            # still in the code, so not really resolved


def test_project_issue_list_uses_only_the_latest_analysis(client, analyzed):
    second = run_analysis(client, analyzed.alice, analyzed.repo["id"])
    listing = client.get(f"/api/projects/{analyzed.pid}/issues?limit=200", headers=analyzed.alice.headers).json()
    assert listing["total"] == second["issue_count"]  # not doubled by history
    assert {i["analysis_id"] for i in listing["items"]} == {second["id"]}
    assert listing["items"][0]["repository_name"] == "acme/api"

    ignored = _issue(client, analyzed.alice, second["id"], OS_IMPORT)
    _set(client, analyzed.alice, ignored["id"], "IGNORED")
    only_ignored = client.get(f"/api/projects/{analyzed.pid}/issues?status=IGNORED", headers=analyzed.bob.headers).json()
    assert only_ignored["total"] == 1
    assert client.get(f"/api/projects/{analyzed.pid}/issues", headers=analyzed.eve.headers).status_code == 404
