"""
Alakoro FiberSense - Configuration
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Alakoro FiberSense Pro"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    REDIS_URL: str = "redis://localhost:6379"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    ENGINE_CPP_PATH: Optional[str] = None

    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
