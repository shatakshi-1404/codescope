from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.core.errors import RepositoryCloneError
from app.models import Analysis, AnalysisFile, AnalysisStatus, Issue, ProjectMember, QualityMetric, SecurityFinding
from app.services import analysis_service
from tests.helpers import add_repo, create_project, error_code, run_analysis

SECRET = "abcd1234abcd1234abcd1234"  # the fake API key in the sample repository
SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
CLONE = "app.services.analysis_service.clone_repository"


# ================================================================ happy path
def test_analysis_runs_end_to_end(client, team):
    repo = add_repo(client, team.alice, team.pid)

    started = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=team.alice.headers)
    assert started.status_code == 202
    assert started.json()["status"] == "PENDING"  # answered immediately; the work runs in the background

    a = client.get(f"/api/analyses/{started.json()['id']}", headers=team.alice.headers).json()
    assert a["status"] == "COMPLETED"
    assert a["progress"] == 100
    assert a["project_id"] == team.pid
    assert a["repository_name"] == "acme/api"
    assert a["branch"] == "main"
    assert a["commit_sha"] == "a" * 40
    assert a["files_analyzed"] == 1
    assert a["function_count"] == 2
    assert a["security_finding_count"] == 2
    assert a["issue_count"] >= 4

    s = a["scores"]
    assert all(0 <= s[k] <= 100 for k in ("overall", "code_quality", "maintainability", "complexity", "security"))
    assert s["security"] < 80  # two HIGH findings must hurt the security score

    assert "acme/api scored" in a["ai_summary"] and "/100" in a["ai_summary"]


def test_issues_are_sorted_worst_first_and_filterable(client, analyzed):
    aid = analyzed.analysis["id"]
    r = client.get(f"/api/analyses/{aid}/issues?limit=200", headers=analyzed.alice.headers)
    items = r.json()["items"]
    assert {"QUAL-002", "QUAL-003", "QUAL-007"} <= {i["rule_id"] for i in items}
    ranks = [SEVERITY_RANK[i["severity"]] for i in items]
    assert ranks == sorted(ranks)
    assert all(i["status"] == "OPEN" for i in items)

    low = client.get(f"/api/analyses/{aid}/issues?severity=LOW&limit=200", headers=analyzed.alice.headers).json()
    assert low["total"] == len(low["items"]) > 0
    assert all(i["severity"] == "LOW" for i in low["items"])

    page = client.get(f"/api/analyses/{aid}/issues?limit=2&offset=1", headers=analyzed.alice.headers).json()
    assert len(page["items"]) == 2 and page["total"] == r.json()["total"]
    assert page["items"][0]["id"] == items[1]["id"]


def test_security_findings_are_labelled_and_never_echo_the_secret(client, analyzed):
    aid = analyzed.analysis["id"]
    r = client.get(f"/api/analyses/{aid}/security", headers=analyzed.alice.headers)
    body = r.json()
    assert body["label"] == "Static Security Checks"
    assert {f["rule_id"] for f in body["items"]} == {"SEC-EVAL", "SEC-HARDCODED-API-KEY"}
    for path in ("security", "issues", "report", "insights", ""):
        text = client.get(f"/api/analyses/{aid}/{path}".rstrip("/"), headers=analyzed.alice.headers).text
        assert SECRET not in text, f"secret value leaked through /{path}"


def test_report_contents(client, analyzed):
    aid = analyzed.analysis["id"]
    r = client.get(f"/api/analyses/{aid}/report", headers=analyzed.alice.headers)
    assert r.status_code == 200
    rep = r.json()
    assert rep["overview"]["files_analyzed"] == 1
    assert rep["overview"]["open_issues"] == rep["overview"]["issues"] > 0
    assert rep["security"]["label"] == "Static Security Checks"
    assert "not a complete security audit" in rep["security"]["disclaimer"]
    assert rep["score_explanation"]
    assert "Automated" in rep["ai_summary_label"] or "generated" in rep["ai_summary_label"]
    assert rep["architecture"]["languages"][0]["language"] == "python"


def test_files_and_insights_endpoints(client, analyzed):
    aid = analyzed.analysis["id"]
    files = client.get(f"/api/analyses/{aid}/files", headers=analyzed.alice.headers).json()
    assert files["total"] == 1
    assert files["items"][0]["path"] == "app.py"
    assert files["items"][0]["issue_count"] > 0

    insights = client.get(f"/api/analyses/{aid}/insights", headers=analyzed.alice.headers).json()
    assert insights["label"] == "AI-assisted analysis"
    assert "No source code is sent" in insights["method"]
    assert insights["recommendations"]
    assert insights["issue_clusters"]


def test_analysis_is_deterministic(client, analyzed):
    second = run_analysis(client, analyzed.alice, analyzed.repo["id"])
    first = analyzed.analysis
    assert second["scores"] == first["scores"]
    assert second["issue_count"] == first["issue_count"]
    assert second["security_finding_count"] == first["security_finding_count"]


def test_history_numbers_analyses_oldest_first(client, analyzed):
    run_analysis(client, analyzed.alice, analyzed.repo["id"])
    history = client.get(f"/api/repositories/{analyzed.repo['id']}/history", headers=analyzed.alice.headers).json()
    assert [p["number"] for p in history] == [1, 2]
    assert history[0]["date"] <= history[1]["date"]
    assert history[0]["overall"] == history[1]["overall"]


def test_the_requested_branch_is_used(client, team):
    repo = add_repo(client, team.alice, team.pid)
    a = run_analysis(client, team.alice, repo["id"], branch="develop")
    assert a["branch"] == "develop"


def test_invalid_branch_is_rejected_and_nothing_is_created(client, team):
    repo = add_repo(client, team.alice, team.pid)
    r = client.post(f"/api/repositories/{repo['id']}/analyze", json={"branch": "--upload-pack=evil"}, headers=team.alice.headers)
    assert r.status_code == 422
    assert error_code(r) == "invalid_branch"
    assert client.get(f"/api/projects/{team.pid}/analyses", headers=team.alice.headers).json()["total"] == 0


# =============================================================== concurrency
def test_cannot_start_a_second_analysis_while_one_is_active(client, team, db):
    repo = add_repo(client, team.alice, team.pid)
    db.add(Analysis(repository_id=repo["id"], status=AnalysisStatus.PENDING))
    db.commit()
    r = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=team.alice.headers)
    assert r.status_code == 409
    assert error_code(r) == "conflict"


def test_unfinished_analyses_have_no_report_yet(client, team, db):
    repo = add_repo(client, team.alice, team.pid)
    pending = Analysis(repository_id=repo["id"], status=AnalysisStatus.RUNNING, progress=40)
    db.add(pending)
    db.commit()
    assert client.get(f"/api/analyses/{pending.id}", headers=team.alice.headers).json()["progress"] == 40
    for path in ("report", "files", "insights"):
        r = client.get(f"/api/analyses/{pending.id}/{path}", headers=team.alice.headers)
        assert r.status_code == 409, path


def test_interrupted_analyses_are_failed_on_startup(client, team, db):
    repo = add_repo(client, team.alice, team.pid)
    rows = [AnalysisStatus.PENDING, AnalysisStatus.RUNNING, AnalysisStatus.COMPLETED]
    for status in rows:
        db.add(Analysis(repository_id=repo["id"], status=status, completed_at=datetime.now(timezone.utc)))
    db.commit()

    assert analysis_service.fail_interrupted_analyses() == 2

    db.expire_all()
    statuses = sorted(s.value for s in db.scalars(select(Analysis.status)))
    assert statuses == ["COMPLETED", "FAILED", "FAILED"]


# ================================================================== failures
def test_a_clone_failure_marks_the_analysis_failed(client, team, monkeypatch):
    def failing_clone(url, branch):
        raise RepositoryCloneError("GitHub is unreachable.")

    monkeypatch.setattr(CLONE, failing_clone)
    repo = add_repo(client, team.alice, team.pid)
    a = run_analysis(client, team.alice, repo["id"])

    assert a["status"] == "FAILED"
    assert a["error_message"] == "GitHub is unreachable."
    assert a["scores"] is None
    assert client.get(f"/api/analyses/{a['id']}/report", headers=team.alice.headers).status_code == 409

    repos = client.get(f"/api/projects/{team.pid}/repositories", headers=team.alice.headers).json()
    assert repos[0]["latest_analysis"]["status"] == "FAILED"
    actions = [x["action"] for x in client.get(f"/api/projects/{team.pid}/activity", headers=team.alice.headers).json()["items"]]
    assert "analysis_failed" in actions

    # a failed run does not block the next attempt
    again = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=team.alice.headers)
    assert again.status_code == 202


def test_unexpected_errors_do_not_leak_internals(client, team, monkeypatch):
    def exploding_clone(url, branch):
        raise RuntimeError("internal path /srv/secret-config exploded")

    monkeypatch.setattr(CLONE, exploding_clone)
    repo = add_repo(client, team.alice, team.pid)
    a = run_analysis(client, team.alice, repo["id"])
    assert a["status"] == "FAILED"
    assert "secret-config" not in (a["error_message"] or "")
    assert "unexpectedly" in a["error_message"]


def test_a_repository_without_supported_files_fails_clearly(client, team, sample_repo):
    (sample_repo / "app.py").unlink()
    (sample_repo / "README.md").write_text("# nothing to analyze\n")
    repo = add_repo(client, team.alice, team.pid)
    a = run_analysis(client, team.alice, repo["id"])
    assert a["status"] == "FAILED"
    assert "No supported source files" in a["error_message"]


def test_one_broken_file_does_not_sink_the_analysis(client, team, sample_repo):
    (sample_repo / "broken.py").write_text("def (:\n")
    repo = add_repo(client, team.alice, team.pid)
    a = run_analysis(client, team.alice, repo["id"])
    assert a["status"] == "COMPLETED"
    assert a["files_analyzed"] == 2
    assert any(w.startswith("broken.py") for w in a["warnings"])


# ============================================================== authorization
@pytest.mark.parametrize(
    "who, expected",
    [("alice", 202), ("dave", 202), ("carol", 202), ("bob", 403), ("eve", 404)],
)
def test_who_can_run_analyses(client, team, who, expected):
    repo = add_repo(client, team.alice, team.pid)
    r = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=getattr(team, who).headers)
    assert r.status_code == expected


@pytest.mark.parametrize("suffix", ["", "/report", "/issues", "/security", "/insights", "/files"])
def test_who_can_read_analysis_data(client, analyzed, suffix):
    url = f"/api/analyses/{analyzed.analysis['id']}{suffix}"
    assert client.get(url, headers=analyzed.bob.headers).status_code == 200   # viewers may read
    stranger = client.get(url, headers=analyzed.eve.headers)
    assert stranger.status_code == 404                                         # strangers learn nothing
    assert error_code(stranger) == "not_found"


def test_history_visibility(client, analyzed):
    url = f"/api/repositories/{analyzed.repo['id']}/history"
    assert client.get(url, headers=analyzed.bob.headers).status_code == 200
    assert client.get(url, headers=analyzed.eve.headers).status_code == 404


def test_changing_the_id_in_the_url_never_exposes_another_users_data(client, analyzed):
    eve_project = create_project(client, analyzed.eve, "Eve's project")
    eve_repo = add_repo(client, analyzed.eve, eve_project["id"], "https://github.com/eve/tool")
    eve_analysis = run_analysis(client, analyzed.eve, eve_repo["id"])

    alice_aid, eve_aid = analyzed.analysis["id"], eve_analysis["id"]
    assert client.get(f"/api/analyses/{eve_aid}", headers=analyzed.eve.headers).status_code == 200
    assert client.get(f"/api/analyses/{alice_aid}", headers=analyzed.eve.headers).status_code == 404
    assert client.get(f"/api/analyses/{eve_aid}", headers=analyzed.alice.headers).status_code == 404
    assert client.get(f"/api/analyses/{eve_aid}/report", headers=analyzed.alice.headers).status_code == 404

    # Eve cannot trigger analyses on Alice's repository either, and no row is created
    before = client.get(f"/api/projects/{analyzed.pid}/analyses", headers=analyzed.alice.headers).json()["total"]
    r = client.post(f"/api/repositories/{analyzed.repo['id']}/analyze", json={}, headers=analyzed.eve.headers)
    assert r.status_code == 404
    after = client.get(f"/api/projects/{analyzed.pid}/analyses", headers=analyzed.alice.headers).json()["total"]
    assert before == after


def test_unknown_ids_return_404(client, team):
    assert client.get("/api/analyses/99999", headers=team.alice.headers).status_code == 404
    assert client.post("/api/repositories/99999/analyze", json={}, headers=team.alice.headers).status_code == 404
    assert client.get("/api/repositories/99999/history", headers=team.alice.headers).status_code == 404


# ============================================================= data lifecycle
def test_deleting_a_project_removes_all_analysis_data(client, analyzed, db):
    assert client.delete(f"/api/projects/{analyzed.pid}", headers=analyzed.alice.headers).status_code == 204
    for model in (Analysis, AnalysisFile, Issue, SecurityFinding, QualityMetric, ProjectMember):
        assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
