from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./storage/docvault.db"
    storage_path: str = "./storage"
    session_cookie_name: str = "docvault_session"
    session_ttl_hours: int = 12
    session_cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
