import os
from datetime import date
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    park_id_objetivo: str = os.getenv("PARK_ID_OBJETIVO", "08e20910d81d42658d4334d3f6d10ac0")
    name_similarity_threshold: float = float(os.getenv("NAME_SIMILARITY_THRESHOLD", "0.66"))
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    # Fecha de arranque del pipeline de leads para determinar legacy_external
    # Drivers/personas con first_seen_at anterior a esta fecha sin origen válido son legacy
    lead_system_start_date: str = os.getenv("LEAD_SYSTEM_START_DATE", "2024-01-01")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

PARK_ID_OBJETIVO = settings.park_id_objetivo
NAME_SIMILARITY_THRESHOLD = settings.name_similarity_threshold
LEAD_SYSTEM_START_DATE = date.fromisoformat(settings.lead_system_start_date)
