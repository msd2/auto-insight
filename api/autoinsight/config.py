from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://autoinsight:autoinsight@localhost:5433/autoinsight"

    @property
    def procrastinate_dsn(self) -> str:
        """Plain-psycopg DSN for Procrastinate, derived from DATABASE_URL."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
