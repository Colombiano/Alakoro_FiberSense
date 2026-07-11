"""Configuration management for Alakoro FiberSense."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Alakoro FiberSense API"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://alakoro:password@postgres:5432/alakoro"
    DATABASE_POOL_SIZE: int = 20

    # Redis (Event Bus)
    REDIS_URL: str = "redis://redis:6379"
    REDIS_DB: int = 0

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # C++ Engine
    C_ENGINE_PATH: str = "/app/engine/libalakoro.so"
    C_ENGINE_ENABLED: bool = True

    # File Storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE: int = 1073741824  # 1GB

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    # Security
    SECRET_KEY: str = "alakoro-fibersense-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Event Channels
    EVENT_CHANNEL_PREFIX: str = "alakoro"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
