from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://autoinsight:autoinsight@localhost:5433/autoinsight"

    # Auth (WP 0.3)
    session_cookie_name: str = "autoinsight_session"
    # Local dev runs over plain http; staging/production set SESSION_COOKIE_SECURE=true.
    session_cookie_secure: bool = False
    session_ttl_hours: int = 24 * 14
    password_reset_ttl_minutes: int = 60
    # Base URL of the web app, used to build password-reset links in emails.
    web_base_url: str = "http://localhost:5173"

    @property
    def procrastinate_dsn(self) -> str:
        """Plain-psycopg DSN for Procrastinate, derived from DATABASE_URL."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
