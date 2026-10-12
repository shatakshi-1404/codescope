import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = "postgresql+psycopg://u:p@localhost:5432/db"
STRONG = "k" * 48


def make(**kwargs) -> Settings:
    return Settings(database_url=DB, _env_file=None, **kwargs)


def test_production_accepts_a_strong_secret():
    assert make(app_env="production", jwt_secret=STRONG).jwt_secret == STRONG


@pytest.mark.parametrize("secret", ["short", "x" * 31, "change-me-to-a-long-random-string-0123456789"])
def test_production_refuses_weak_or_placeholder_secrets(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        make(app_env="production", jwt_secret=secret)


def test_development_allows_a_placeholder_secret():
    assert make(app_env="development", jwt_secret="change-me").app_env == "development"


def test_cors_origins_are_split_and_trimmed():
    s = make(app_env="development", jwt_secret=STRONG, cors_origins=" http://a.test , http://b.test ,")
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]


# ---------------------------------------------------------- hosted-database URLs
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg://u:p@h/db?sslmode=require"),
        ("  postgresql://u:p@h/db  ", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),  # already right: untouched
        ("sqlite:///x.db", "sqlite:///x.db"),
    ],
)
def test_database_url_is_pointed_at_the_psycopg_driver(raw, expected):
    s = Settings(database_url=raw, jwt_secret=STRONG, app_env="development", _env_file=None)
    assert s.database_url == expected


def test_hosting_related_defaults():
    fields = Settings.model_fields
    assert fields["cors_origin_regex"].default == ""
    assert fields["auth_rate_limit_per_minute"].default == 30
    assert fields["max_repo_mb"].default == 300
