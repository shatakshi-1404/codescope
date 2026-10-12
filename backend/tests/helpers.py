from dataclasses import dataclass

PASSWORD = "Passw0rd123"


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    email: str
    headers: dict
    refresh_token: str


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def error_code(response) -> str:
    return response.json()["error"]["code"]


def register(client, name: str = "Alice", email: str | None = None) -> Account:
    email = email or f"{name.lower()}@example.com"
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    d = r.json()
    return Account(
        id=d["user"]["id"],
        name=name,
        email=email.lower(),
        headers=bearer(d["access_token"]),
        refresh_token=d["refresh_token"],
    )


def create_project(client, who: Account, name: str = "Acme API", description: str | None = None) -> dict:
    r = client.post("/api/projects", json={"name": name, "description": description}, headers=who.headers)
    assert r.status_code == 201, r.text
    return r.json()


def add_member(client, actor: Account, project_id: int, member: Account, role: str = "MEMBER") -> dict:
    r = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": member.email, "role": role},
        headers=actor.headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def member_row_id(client, actor: Account, project_id: int, email: str) -> int:
    r = client.get(f"/api/projects/{project_id}/members", headers=actor.headers)
    assert r.status_code == 200, r.text
    return next(m["id"] for m in r.json() if m["email"] == email)


def add_repo(client, who: Account, project_id: int, url: str = "https://github.com/acme/api") -> dict:
    r = client.post(f"/api/projects/{project_id}/repositories", json={"url": url}, headers=who.headers)
    assert r.status_code == 201, r.text
    return r.json()


def run_analysis(client, who: Account, repo_id: int, branch: str | None = None) -> dict:
    """Starts an analysis and returns its FINAL state.
    TestClient waits for FastAPI background tasks, so the job is finished when POST returns."""
    r = client.post(
        f"/api/repositories/{repo_id}/analyze",
        json={"branch": branch} if branch else {},
        headers=who.headers,
    )
    assert r.status_code == 202, r.text
    final = client.get(f"/api/analyses/{r.json()['id']}", headers=who.headers)
    assert final.status_code == 200, final.text
    return final.json()
