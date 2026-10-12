import pytest

from app.core import ratelimit
from app.core.config import settings
from app.core.ratelimit import SlidingWindowLimiter
from tests.helpers import PASSWORD, bearer, error_code


# ============================================================ the limiter itself
class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_blocks_after_the_limit_and_recovers_when_the_window_passes():
    clock = Clock()
    limiter = SlidingWindowLimiter(window_seconds=60, clock=clock)
    assert [limiter.allow("a", 3) for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("b", 3)  # keys are independent
    clock.now += 59
    assert not limiter.allow("a", 3)  # still inside the window
    clock.now += 2
    assert limiter.allow("a", 3)      # window has passed


def test_a_limit_of_zero_means_unlimited():
    limiter = SlidingWindowLimiter(clock=Clock())
    assert all(limiter.allow("a", 0) for _ in range(500))


def test_memory_stays_bounded():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_keys=5, clock=clock)
    for i in range(50):
        limiter.allow(f"k{i}", 3)
    assert len(limiter._hits) <= 5


# ================================================================ through the API
@pytest.fixture()
def limited(monkeypatch):
    """Switch the limiter on: 6 per IP per minute, 3 per e-mail per minute."""
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 6)
    ratelimit.auth_limiter.reset()
    yield
    ratelimit.auth_limiter.reset()


def _register(client, n, headers=None):
    return client.post(
        "/api/auth/register",
        json={"name": f"User {n}", "email": f"user{n}@example.com", "password": PASSWORD},
        headers=headers or {},
    )


def _login(client, email, headers=None, password="Wrong12345"):
    return client.post("/api/auth/login", json={"email": email, "password": password}, headers=headers or {})


def test_too_many_requests_from_one_ip_are_refused(client, limited):
    first = _register(client, 0)
    assert first.status_code == 201
    for n in range(1, 6):
        assert _register(client, n).status_code == 201
    blocked = _register(client, 99)
    assert blocked.status_code == 429
    assert error_code(blocked) == "rate_limited"
    assert "wait a minute" in blocked.json()["error"]["message"]

    # ordinary signed-in traffic is NOT throttled
    token = first.json()["access_token"]
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": first.json()["refresh_token"]}).status_code == 200


def test_a_forged_forwarded_for_header_does_not_evade_the_ip_limit(client, limited):
    """Behind a proxy only the LAST X-Forwarded-For entry (added by the proxy) is trusted."""
    for n in range(6):
        r = _register(client, n, headers={"X-Forwarded-For": f"10.0.0.{n}, 9.9.9.9"})  # client lies about the first entry
        assert r.status_code == 201
    assert _register(client, 50, headers={"X-Forwarded-For": "10.0.0.77, 9.9.9.9"}).status_code == 429
    # a genuinely different caller (different last entry) has its own allowance
    assert _register(client, 51, headers={"X-Forwarded-For": "10.0.0.1, 8.8.8.8"}).status_code == 201


def test_brute_forcing_one_account_is_stopped_even_from_many_ips(client, limited):
    victim = "victim@example.com"
    client.post("/api/auth/register", json={"name": "Victim", "email": victim, "password": PASSWORD},
                headers={"X-Forwarded-For": "7.7.7.7"})
    codes = [_login(client, victim, headers={"X-Forwarded-For": f"1.1.1.{i}"}).status_code for i in range(5)]
    assert codes == [401, 401, 401, 429, 429]          # the 4th guess is refused, whatever the IP
    # and it holds even when the attacker would now supply the right password
    assert _login(client, victim, headers={"X-Forwarded-For": "1.1.1.200"}, password=PASSWORD).status_code == 429
    # other accounts are unaffected
    assert _login(client, "someone-else@example.com", headers={"X-Forwarded-For": "1.1.1.201"}).status_code == 401


def test_the_account_limit_ignores_letter_case(client, limited):
    for i, email in enumerate(["Case@Example.com", "case@example.com", "CASE@EXAMPLE.COM"]):
        assert _login(client, email, headers={"X-Forwarded-For": f"2.2.2.{i}"}).status_code == 401
    assert _login(client, "case@example.COM", headers={"X-Forwarded-For": "2.2.2.9"}).status_code == 429


def test_password_reset_requests_are_limited_per_account(client, limited):
    register_ok = client.post("/api/auth/register", json={"name": "R", "email": "reset@example.com", "password": PASSWORD})
    assert register_ok.status_code == 201
    codes = [
        client.post("/api/auth/forgot-password", json={"email": "reset@example.com"},
                    headers={"X-Forwarded-For": f"3.3.3.{i}"}).status_code
        for i in range(5)
    ]
    assert codes == [200, 200, 200, 429, 429]


def test_the_limiter_can_be_turned_off(client):
    # AUTH_RATE_LIMIT_PER_MINUTE=0 is the suite default
    assert settings.auth_rate_limit_per_minute == 0
    assert all(_login(client, "nobody@example.com").status_code == 401 for _ in range(15))
