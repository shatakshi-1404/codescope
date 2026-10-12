"""CORS matters when the web app (Vercel) and the API (Render) live on different origins."""
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app as real_app
from app.main import cors_options

PREVIEWS = r"https://codescope(-[a-z0-9-]+)?\.vercel\.app"


def make_client(**kwargs) -> TestClient:
    s = Settings(
        database_url="postgresql://u:p@h/db", jwt_secret="k" * 48, app_env="production", _env_file=None, **kwargs
    )
    mini = FastAPI()
    mini.add_middleware(CORSMiddleware, **cors_options(s))

    @mini.post("/x")
    def x():
        return {}

    return TestClient(mini)


def preflight(client: TestClient, origin: str, path: str = "/x"):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


def test_a_listed_origin_is_allowed():
    r = preflight(make_client(cors_origins="https://codescope.vercel.app"), "https://codescope.vercel.app")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://codescope.vercel.app"
    assert "authorization" in r.headers["access-control-allow-headers"].lower()


def test_several_origins_can_be_listed():
    c = make_client(cors_origins=" https://a.test , https://b.test ")
    assert preflight(c, "https://a.test").status_code == 200
    assert preflight(c, "https://b.test").status_code == 200


def test_an_unlisted_origin_is_refused():
    r = preflight(make_client(cors_origins="https://codescope.vercel.app"), "https://evil.example")
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_preview_deployments_match_the_regex():
    c = make_client(cors_origins="https://codescope.vercel.app", cors_origin_regex=PREVIEWS)
    assert preflight(c, "https://codescope-git-feature-x-myteam.vercel.app").status_code == 200
    assert preflight(c, "https://codescope.vercel.app").status_code == 200


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.vercel.app",
        "https://codescope.vercel.app.evil.com",
        "https://evil-codescope.vercel.app",
        "http://codescope.vercel.app",  # wrong scheme
    ],
)
def test_lookalike_origins_do_not_match_the_regex(origin):
    c = make_client(cors_origins="https://codescope.vercel.app", cors_origin_regex=PREVIEWS)
    assert preflight(c, origin).status_code == 400


def test_the_regex_is_off_by_default():
    c = make_client(cors_origins="https://codescope.vercel.app")
    assert preflight(c, "https://codescope-git-x.vercel.app").status_code == 400


def test_the_real_app_allows_the_local_dev_frontend():
    r = preflight(TestClient(real_app), "http://localhost:5173", path="/api/auth/login")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
