import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True

    # Database settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://docubrain:docubrain123@docubrain-postgres:5432/docubrain')

    # Google Cloud Storage settings
    GCS_BUCKET_NAME: str = "mehar-ocr-test"

    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

    # Vision AI model settings
    VISION_MODEL_NAME: str = "gemini-1.5-flash"

    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI OCR Application"

    # Logging settings
    LOG_LEVEL: str = "INFO"

@lru_cache()
def get_settings():
    return Settings()
