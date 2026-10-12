"""
Shared fixtures.

Integration tests use a REAL PostgreSQL database called <your db>_test (created
automatically). Pure unit tests (analysis engine, URL parsing, permissions, ...)
never touch the database.
"""
import os
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

# Settings reads the environment the first time app.core.config is imported,
# so these defaults must exist before any `app` import.
# The suite creates dozens of accounts from one IP; rate-limit tests switch the limiter on themselves.
os.environ.setdefault("AUTH_RATE_LIMIT_PER_MINUTE", "0")
os.environ.setdefault("JWT_SECRET", "test-only-secret-0123456789-abcdefghijklmnopqrstuvwxyz")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://codescope:codescope_dev_password@localhost:5432/codescope",
)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import URL, make_url  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

SAMPLE_APP = '''import os
import json

API_KEY = "abcd1234abcd1234abcd1234"


def run(user_input):
    return eval(user_input)


def tangled(a, b, c, d, e, f, g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
    return 0
'''
# The sample deliberately contains known problems:
#   unused imports (os, json), 7 parameters, nesting depth 5,
#   eval() and a hardcoded API key.


def _test_db_url() -> URL:
    explicit = os.environ.get("TEST_DATABASE_URL")
    url = make_url(explicit or os.environ["DATABASE_URL"])
    if not explicit:
        url = url.set(database=f"{url.database}_test")
    # Safety net: the suite TRUNCATEs every table, so it must never point at real data.
    if not (url.database or "").endswith("_test"):
        raise RuntimeError(f"Refusing to run tests against database '{url.database}'. Its name must end in _test.")
    return url


def _ensure_database(url: URL) -> None:
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def engine():
    from app.core.database import Base
    import app.models  # noqa: F401  (registers every table)

    url = _test_db_url()
    _ensure_database(url)
    eng = create_engine(url, pool_pre_ping=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def sample_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(SAMPLE_APP)
    return repo


@pytest.fixture()
def client(engine, session_factory, sample_repo, monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.database import Base, get_db
    from app.ingestion.git_client import ClonedRepo
    from app.main import app
    from app.services import analysis_service, repository_service

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Background analysis jobs open their own sessions: point them at the test DB.
    monkeypatch.setattr(analysis_service, "SessionLocal", session_factory)
    # No network, no real git: a fake GitHub that "clones" the sample repository.
    monkeypatch.setattr(repository_service, "fetch_default_branch", lambda url: "main")

    @contextmanager
    def fake_clone(url, branch):
        yield ClonedRepo(path=sample_repo, branch=branch or "main", commit_sha="a" * 40)

    monkeypatch.setattr(analysis_service, "clone_repository", fake_clone)

    # No `with`: the lifespan hook is not run. TestClient still waits for background tasks.
    yield TestClient(app)

    app.dependency_overrides.clear()
    with engine.begin() as conn:
        names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def db(client, session_factory):
    """Direct DB access for assertions. Depends on `client` so it is closed BEFORE the
    teardown TRUNCATE (an open transaction would block the TRUNCATE)."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def team(client):
    """
    One project with every role:
      alice = OWNER, dave = ADMIN, carol = MEMBER, bob = VIEWER,
      eve   = a registered user who is NOT in the project (the stranger).
    """
    from tests import helpers as h

    alice = h.register(client, "Alice")
    project = h.create_project(client, alice)
    bob, carol, dave, eve = (h.register(client, n) for n in ("Bob", "Carol", "Dave", "Eve"))
    h.add_member(client, alice, project["id"], bob, "VIEWER")
    h.add_member(client, alice, project["id"], carol, "MEMBER")
    h.add_member(client, alice, project["id"], dave, "ADMIN")
    return SimpleNamespace(alice=alice, bob=bob, carol=carol, dave=dave, eve=eve, project=project, pid=project["id"])


@pytest.fixture()
def analyzed(client, team):
    """`team` plus one repository with one COMPLETED analysis of the sample repo."""
    from tests import helpers as h

    team.repo = h.add_repo(client, team.alice, team.pid)
    team.analysis = h.run_analysis(client, team.alice, team.repo["id"])
    return team
