"""Central application settings, read from environment variables (.env in
development, real env vars / secrets in production). See .env.example at the
repo root for the full list and what each one does.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = "development"
    app_base_url: str = "http://localhost:3000"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 12

    # Database / broker
    database_url: str = "postgresql+psycopg://tp_user:tp_password@localhost:5432/tp_manager"
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Cliniccards integration (see app/integrations/cliniccards)
    cliniccards_mode: str = "mock"  # "mock" | "http"
    cliniccards_api_url: str | None = None
    cliniccards_api_key: str | None = None
    cliniccards_api_key_header: str = "Authorization"
    cliniccards_patients_path: str = "/patients"
    cliniccards_appointments_path: str = "/appointments"
    cliniccards_appointment_by_id_path: str = "/appointments/{appointment_id}"
    cliniccards_patient_documents_path: str = "/patients/{patient_id}/documents"
    cliniccards_patient_images_path: str = "/patients/{patient_id}/images"
    cliniccards_webhook_secret: str | None = None

    # Telegram
    telegram_bot_token: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
