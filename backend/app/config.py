from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    secret_key: str = "dev-secret-key-change-in-production"
    database_url: str = "sqlite+aiosqlite:///./fpvconfigs.db"
    configs_dir: str = "../configs"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    max_upload_size: int = 64 * 1024  # 64KB

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
