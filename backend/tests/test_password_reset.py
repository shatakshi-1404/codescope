from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.core.config import settings
from app.models import PasswordResetToken
from tests.helpers import PASSWORD, error_code, register

NEW_PASSWORD = "NewPassw0rd9"


def _forgot(client, email):
    return client.post("/api/auth/forgot-password", json={"email": email})


def _reset(client, token, password=NEW_PASSWORD):
    return client.post("/api/auth/reset-password", json={"token": token, "new_password": password})


def _login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_response_does_not_reveal_whether_the_account_exists(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    register(client)
    known = _forgot(client, "alice@example.com").json()
    unknown = _forgot(client, "nobody@example.com").json()
    assert known["message"] == unknown["message"]
    assert unknown["dev_reset_token"] is None


def test_token_is_only_returned_in_development(client, db, monkeypatch):
    register(client)
    monkeypatch.setattr(settings, "app_env", "production")
    body = _forgot(client, "alice@example.com").json()
    assert body["dev_reset_token"] is None
    # the token still exists server-side (it would be emailed)
    assert db.scalar(select(func.count()).select_from(PasswordResetToken)) == 1


def test_full_reset_flow(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    alice = register(client)
    token = _forgot(client, alice.email).json()["dev_reset_token"]
    assert token

    r = _reset(client, token)
    assert r.status_code == 200

    assert _login(client, alice.email, NEW_PASSWORD).status_code == 200
    assert _login(client, alice.email, PASSWORD).status_code == 401
    # every existing session is signed out
    assert client.post("/api/auth/refresh", json={"refresh_token": alice.refresh_token}).status_code == 401


def test_a_reset_token_works_only_once(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    alice = register(client)
    token = _forgot(client, alice.email).json()["dev_reset_token"]
    assert _reset(client, token).status_code == 200
    again = _reset(client, token, "AnotherPassw0rd")
    assert again.status_code == 422
    assert error_code(again) == "business_rule_violation"


def test_a_newer_link_invalidates_the_older_one(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    alice = register(client)
    old = _forgot(client, alice.email).json()["dev_reset_token"]
    new = _forgot(client, alice.email).json()["dev_reset_token"]
    assert _reset(client, old).status_code == 422
    assert _reset(client, new).status_code == 200


def test_expired_token_is_rejected(client, db, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    alice = register(client)
    token = _forgot(client, alice.email).json()["dev_reset_token"]
    db.execute(update(PasswordResetToken).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    db.commit()
    assert _reset(client, token).status_code == 422


def test_unknown_token_is_rejected(client):
    r = _reset(client, "x" * 40)
    assert r.status_code == 422
    assert error_code(r) == "business_rule_violation"


def test_weak_new_password_is_rejected_without_burning_the_token(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    alice = register(client)
    token = _forgot(client, alice.email).json()["dev_reset_token"]
    weak = _reset(client, token, "abcdefgh")
    assert weak.status_code == 422
    assert error_code(weak) == "validation_error"
    assert _reset(client, token).status_code == 200
