from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables. No secrets in code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    cors_origins: str = "http://localhost:5173"
    # Optional regex of extra allowed origins, e.g. Vercel preview deployments:
    #   https://codescope(-[a-z0-9-]+)?\.vercel\.app
    cors_origin_regex: str = ""
    app_env: str = "production"  # "development" enables dev-only conveniences
    password_reset_expire_minutes: int = 30
    # Login/register/reset throttling (per IP; per e-mail it is a third of this). 0 turns it off.
    auth_rate_limit_per_minute: int = 30
    # Largest repository (MB) the analyzer will accept. Lower it on small hosting plans.
    max_repo_mb: int = 300

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, v: str) -> str:
        """Hosts such as Render hand out postgres:// or postgresql:// URLs.
        SQLAlchemy would then look for the old psycopg2 driver, so name psycopg 3 explicitly."""
        v = v.strip()
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @model_validator(mode="after")
    def _reject_weak_secret_in_production(self) -> "Settings":
        if self.app_env == "production":
            weak = len(self.jwt_secret) < 32 or self.jwt_secret.lower().startswith("change-me")
            if weak:
                raise ValueError(
                    "JWT_SECRET must be a random string of at least 32 characters when APP_ENV=production. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
