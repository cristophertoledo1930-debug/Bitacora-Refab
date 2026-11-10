from functools import lru_cache
from zoneinfo import ZoneInfo
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        hide_input_in_errors=True,
        extra="ignore"
    )

    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:8070"
    APP_TIMEZONE: str = "America/Santiago"
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/qrlabhub_dev"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/qrlabhub_test"

    ADMIN_API_KEY: str = "labhub-dev-admin-key-2026"
    GOOGLE_FORMS_SECRET: str = Field(default="", repr=False)
    GOOGLE_FORM_URL: str = ""
    DASHBOARD_NEW_RECORD_URL: str = "/r/token-general"
    GOOGLE_SHEETS_ID: str = ""
    GOOGLE_SHEETS_TAB: str = "Respuestas de formulario 1"
    GOOGLE_SHEETS_CREDENTIALS: str = "credenciales.json"

    # SMTP Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_TLS: bool = False
    SMTP_SSL: bool = False
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = Field(default="", repr=False)
    REPORT_FROM: str = "no-reply@qrlabhub.local"
    REPORT_TO: str = "coordinador@qrlabhub.local"
    EMAIL_ENABLED: bool = False
    LOCAL_SMTP_ENABLED: bool = False
    LOCAL_DESKTOP_ACCESS: bool = False

    REPORT_OUTPUT_DIR: str = "storage/reports"
    REPORT_INITIAL_MONTH: str = "2026-01"
    REPORT_SEND_DAY: int = Field(default=1, ge=1, le=28)
    REPORT_SEND_HOUR: int = Field(default=8, ge=0, le=23)
    REPORT_SOURCE: str = "google_forms"
    REPORT_AUTO_SEND_FROM: str = ""

    @field_validator("REPORT_SOURCE")
    @classmethod
    def valid_report_source(cls, value):
        if value not in {"", "manual", "google_forms", "esp32"}:
            raise ValueError("REPORT_SOURCE inválido")
        return value

    @field_validator("REPORT_AUTO_SEND_FROM", "REPORT_INITIAL_MONTH")
    @classmethod
    def valid_report_month(cls, value, info):
        from datetime import date
        if not value and info.field_name == "REPORT_AUTO_SEND_FROM":
            return value
        try:
            parsed = date.fromisoformat(value + "-01")
            if parsed.strftime("%Y-%m") != value:
                raise ValueError()
        except ValueError:
            raise ValueError("Periodo debe tener formato YYYY-MM") from None
        return value

    @model_validator(mode="after")
    def secure_smtp(self):
        self.validate_smtp_security()
        return self

    def validate_smtp_security(self):
        loopback = self.SMTP_HOST in {"localhost", "127.0.0.1", "::1"}
        if self.LOCAL_SMTP_ENABLED and not loopback:
            raise ValueError("El SMTP local requiere un host loopback.")
        if self.SMTP_SSL and self.SMTP_TLS:
            raise ValueError("Seleccione SMTP_SSL o SMTP_TLS, no ambos.")
        if self.SMTP_USERNAME and not (self.SMTP_TLS or self.SMTP_SSL or (loopback and self.LOCAL_SMTP_ENABLED)):
            raise ValueError("SMTP autenticado requiere TLS o SSL.")

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.APP_TIMEZONE)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
