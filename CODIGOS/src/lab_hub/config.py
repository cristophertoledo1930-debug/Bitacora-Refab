from functools import lru_cache
import os
from zoneinfo import ZoneInfo
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:8070"
    APP_TIMEZONE: str = "America/Santiago"
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/qrlabhub_dev"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/qrlabhub_test"

    ADMIN_API_KEY: str = "labhub-dev-admin-key-2026"

    # SMTP Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_TLS: bool = False
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    REPORT_FROM: str = "no-reply@qrlabhub.local"
    REPORT_TO: str = "coordinador@qrlabhub.local"
    EMAIL_ENABLED: bool = False
    LOCAL_SMTP_ENABLED: bool = False
    LOCAL_DESKTOP_ACCESS: bool = False

    REPORT_OUTPUT_DIR: str = "storage/reports"
    REPORT_INITIAL_MONTH: str = "2026-01"

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.APP_TIMEZONE)


@lru_cache()
def get_settings() -> Settings:
    return Settings()

