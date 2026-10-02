"""Application settings, loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "async-api"
    app_env: str = "dev"
    debug: bool = False

    secret_key: str = "dev-only-insecure-secret-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30

    database_url: str = "sqlite+aiosqlite:///./api.db"

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    cors_origins: str = '["http://localhost:3000"]'

    @property
    def cors_origin_list(self) -> list[str]:
        try:
            parsed = json.loads(self.cors_origins)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except json.JSONDecodeError:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this, never Settings() directly."""
    return Settings()
