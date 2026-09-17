"""Central application settings, read from environment variables (.env in
development, real env vars / secrets in production). See .env.example at the
repo root for the full list and what each one does.
"""
from functools import lru_cache

from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, v: str) -> str:
        # Managed Postgres providers (Railway, Heroku, etc.) hand out plain
        # "postgresql://" / "postgres://" URLs; SQLAlchemy then defaults to
        # psycopg2, which isn't installed here (only psycopg v3 is).
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Cliniccards integration (see app/integrations/cliniccards)
    cliniccards_mode: str = "mock"  # "mock" | "http"
    cliniccards_api_url: str | None = None
    cliniccards_api_key: str | None = None
    cliniccards_api_key_header: str = "Token"
    cliniccards_patients_path: str = "/patients"
    cliniccards_appointments_path: str = "/visits"
    cliniccards_appointment_by_id_path: str = "/visits/{appointment_id}"
    cliniccards_patient_documents_path: str = "/files/{patient_id}"
    cliniccards_patient_images_path: str = "/files/{patient_id}"
    cliniccards_file_path: str = "/file"
    cliniccards_sync_days_back: int = 1
    cliniccards_sync_days_ahead: int = 60
    cliniccards_webhook_secret: str | None = None
    # Runs the sync in-process (no separate worker needed — see
    # app/jobs/periodic_sync.py) every N minutes, in addition to the manual
    # "Sync now" button. Celery + celery-beat also has this same task
    # scheduled, but only if that worker is actually deployed separately.
    cliniccards_auto_sync_minutes: int = 30

    # We don't keep clinical photos/x-rays forever — once a case's
    # consultation is this many days in the past, the image files are
    # purged (see app/jobs/periodic_image_cleanup.py). Everything else
    # about the case (diagnosis, analysis answers, findings) is untouched.
    image_retention_days: int = 7

    # Telegram
    telegram_bot_token: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
