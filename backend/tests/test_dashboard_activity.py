from tests.helpers import register


def test_new_users_get_honest_empty_states(client):
    zoe = register(client, "Zoe")
    d = client.get("/api/dashboard", headers=zoe.headers).json()
    assert d["stats"] == {
        "projects": 0, "repositories": 0, "repositories_analyzed": 0, "open_issues": 0, "average_quality": None,
    }
    assert d["trend"] == [] and d["recent_analyses"] == []
    assert sum(d["issue_distribution"].values()) == 0
    assert set(d["issue_distribution"]) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_dashboard_reflects_the_latest_analysis(client, analyzed):
    d = client.get("/api/dashboard", headers=analyzed.alice.headers).json()
    a = analyzed.analysis
    assert d["stats"]["projects"] == 1
    assert d["stats"]["repositories"] == d["stats"]["repositories_analyzed"] == 1
    assert d["stats"]["open_issues"] == a["issue_count"]
    assert d["stats"]["average_quality"] == round(a["scores"]["overall"], 1)
    assert d["recent_analyses"][0]["id"] == a["id"]
    assert d["recent_analyses"][0]["quality"] == a["scores"]["overall"]
    assert d["security_distribution"]["HIGH"] == 2


def test_history_does_not_inflate_the_dashboard(client, analyzed):
    from tests.helpers import run_analysis

    run_analysis(client, analyzed.alice, analyzed.repo["id"])
    d = client.get("/api/dashboard", headers=analyzed.alice.headers).json()
    assert d["stats"]["open_issues"] == analyzed.analysis["issue_count"]  # latest only
    assert len(d["recent_analyses"]) == 2                                  # but both are listed
    assert len(d["trend"]) == 1                                            # trend averages per day


def test_dashboards_are_isolated_between_users(client, analyzed):
    eve = client.get("/api/dashboard", headers=analyzed.eve.headers).json()
    assert eve["stats"]["projects"] == 0
    assert eve["recent_analyses"] == [] and eve["trend"] == []
    bob = client.get("/api/dashboard", headers=analyzed.bob.headers).json()  # a viewer sees the project's data
    assert bob["stats"]["repositories_analyzed"] == 1


def test_project_activity_tells_the_story(client, analyzed):
    r = client.get(f"/api/projects/{analyzed.pid}/activity?limit=100", headers=analyzed.alice.headers)
    body = r.json()
    actions = [a["action"] for a in body["items"]]
    assert {"project_created", "member_invited", "repository_added", "analysis_started", "analysis_completed"} <= set(actions)
    assert actions[0] == "analysis_completed"  # newest first

    details = [a["detail"] for a in body["items"]]
    assert "Alice ran an analysis on acme/api" in details
    assert any("Bob was added as VIEWER" in d for d in details)
    assert all(a["user_name"] for a in body["items"])


def test_activity_pagination(client, analyzed):
    page = client.get(f"/api/projects/{analyzed.pid}/activity?limit=2", headers=analyzed.alice.headers).json()
    assert len(page["items"]) == 2
    assert page["total"] >= 5


def test_activity_is_private_to_project_members(client, analyzed):
    assert client.get(f"/api/projects/{analyzed.pid}/activity", headers=analyzed.eve.headers).status_code == 404
    assert client.get(f"/api/projects/{analyzed.pid}/activity", headers=analyzed.bob.headers).status_code == 200

    mine = client.get("/api/activity", headers=analyzed.bob.headers).json()
    assert mine["total"] > 0
    stranger = client.get("/api/activity", headers=analyzed.eve.headers).json()
    assert stranger["total"] == 0 and stranger["items"] == []
