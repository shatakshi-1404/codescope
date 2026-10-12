from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import func, select, update

from app.core.config import settings
from app.models import AuditLog, RefreshToken, User
from tests.helpers import PASSWORD, bearer, error_code, register


def _login(client, email, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _payload(sub, *, kind="access", lifetime=timedelta(minutes=5)):
    now = datetime.now(timezone.utc)
    return {"sub": str(sub), "type": kind, "iat": now, "exp": now + lifetime}


# ------------------------------------------------------------------ register
def test_register_returns_tokens_and_a_safe_user(client):
    r = client.post("/api/auth/register", json={"name": "Alice", "email": "Alice@Example.com", "password": PASSWORD})
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "alice@example.com"  # normalized
    assert "password_hash" not in body["user"]
    assert PASSWORD not in r.text


def test_password_is_stored_as_an_argon2_hash(client, db):
    register(client)
    stored = db.scalar(select(User.password_hash))
    assert stored.startswith("$argon2")
    assert PASSWORD not in stored


def test_duplicate_email_is_rejected_case_insensitively(client):
    register(client, "Alice", "alice@example.com")
    r = client.post("/api/auth/register", json={"name": "Imposter", "email": "ALICE@example.com", "password": PASSWORD})
    assert r.status_code == 409
    assert error_code(r) == "conflict"


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"name": "A", "email": "a@example.com", "password": "short1"}, "password"),
        ({"name": "A", "email": "a@example.com", "password": "abcdefgh"}, "password"),
        ({"name": "A", "email": "a@example.com", "password": "12345678"}, "password"),
        ({"name": "A", "email": "not-an-email", "password": PASSWORD}, "email"),
        ({"name": "   ", "email": "a@example.com", "password": PASSWORD}, "name"),
    ],
)
def test_register_rejects_invalid_input(client, db, payload, field):
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 422
    assert error_code(r) == "validation_error"
    assert field in [d["field"] for d in r.json()["error"]["details"]]
    assert db.scalar(select(func.count()).select_from(User)) == 0


# --------------------------------------------------------------------- login
def test_login_succeeds_and_is_audited(client, db):
    register(client)
    r = _login(client, "alice@example.com")
    assert r.status_code == 200
    assert r.json()["user"]["name"] == "Alice"
    logins = db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "login"))
    assert logins == 1


def test_wrong_password_and_unknown_user_look_identical(client):
    register(client)
    wrong = _login(client, "alice@example.com", "Wrong12345")
    unknown = _login(client, "nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # no account enumeration


def test_disabled_user_cannot_login_or_use_an_existing_token(client, db):
    alice = register(client)
    db.execute(update(User).where(User.id == alice.id).values(is_active=False))
    db.commit()
    assert _login(client, alice.email).status_code == 401
    assert client.get("/api/auth/me", headers=alice.headers).status_code == 401


# ------------------------------------------------------------- access tokens
def test_valid_token_returns_the_current_user(client):
    alice = register(client)
    r = client.get("/api/auth/me", headers=alice.headers)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


def test_missing_token_is_rejected(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert error_code(r) == "unauthorized"


def test_garbage_token_is_rejected(client):
    assert client.get("/api/auth/me", headers=bearer("not.a.jwt")).status_code == 401


def test_expired_token_is_rejected(client):
    alice = register(client)
    token = jwt.encode(_payload(alice.id, lifetime=timedelta(minutes=-1)), settings.jwt_secret, algorithm="HS256")
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_token_signed_with_another_secret_is_rejected(client):
    alice = register(client)
    token = jwt.encode(_payload(alice.id), "x" * 48, algorithm="HS256")
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_unsigned_alg_none_token_is_rejected(client):
    alice = register(client)
    token = jwt.encode(_payload(alice.id), None, algorithm="none")
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_a_token_of_the_wrong_type_is_rejected(client):
    alice = register(client)
    token = jwt.encode(_payload(alice.id, kind="refresh"), settings.jwt_secret, algorithm="HS256")
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(client):
    alice = register(client)
    assert client.get("/api/auth/me", headers=bearer(alice.refresh_token)).status_code == 401


# ------------------------------------------------------------ refresh tokens
def test_refresh_rotates_the_token(client):
    alice = register(client)
    first = client.post("/api/auth/refresh", json={"refresh_token": alice.refresh_token})
    assert first.status_code == 200
    new = first.json()
    assert new["refresh_token"] != alice.refresh_token

    # the used token is dead (single use) ...
    assert client.post("/api/auth/refresh", json={"refresh_token": alice.refresh_token}).status_code == 401
    # ... the new pair works
    assert client.get("/api/auth/me", headers=bearer(new["access_token"])).status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": new["refresh_token"]}).status_code == 200


def test_unknown_refresh_token_is_rejected(client):
    assert client.post("/api/auth/refresh", json={"refresh_token": "nope"}).status_code == 401


def test_expired_refresh_token_is_rejected(client, db):
    alice = register(client)
    db.execute(update(RefreshToken).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    db.commit()
    assert client.post("/api/auth/refresh", json={"refresh_token": alice.refresh_token}).status_code == 401


def test_only_a_hash_of_the_refresh_token_is_stored(client, db):
    alice = register(client)
    hashes = list(db.scalars(select(RefreshToken.token_hash)))
    assert hashes and alice.refresh_token not in hashes
    assert all(len(h) == 64 for h in hashes)


def test_logout_revokes_the_refresh_token_and_is_idempotent(client):
    alice = register(client)
    assert client.post("/api/auth/logout", json={"refresh_token": alice.refresh_token}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": alice.refresh_token}).status_code == 401
    assert client.post("/api/auth/logout", json={"refresh_token": alice.refresh_token}).status_code == 204
    assert client.post("/api/auth/logout", json={"refresh_token": "garbage"}).status_code == 204
