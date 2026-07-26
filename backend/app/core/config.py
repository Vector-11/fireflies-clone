"""Application settings, read from the environment (and an optional .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Fireflies Clone API"
    api_v1_prefix: str = "/api/v1"

    # SQLAlchemy URL. SQLite by default, as required by the assignment.
    database_url: str = "sqlite:///./fireflies.db"

    # Browser origins allowed to call this API.
    cors_origins: str = "http://localhost:3000"
    # Optional regex for dynamic origins, e.g. Vercel preview URLs.
    cors_origin_regex: str | None = None

    # Load seed meetings on startup when the database is empty.
    seed_on_startup: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()


settings = get_settings()
