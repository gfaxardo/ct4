"""
Configuración de la aplicación (Pydantic Settings).

Valores sensibles vía variables de entorno o .env.
En producción: DATABASE_URL, CORS_ORIGINS, ENVIRONMENT=production.
"""
import os
from datetime import date
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración cargada desde variables de entorno.
    """
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/ct4")
    log_level: str = "INFO"
    environment: str = os.getenv("ENVIRONMENT", "development")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    park_id_objetivo: str = "08e20910d81d42658d4334d3f6d10ac0"
    name_similarity_threshold: float = 0.66
    admin_token: str = ""
    lead_system_start_date: str = "2024-01-01"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
PARK_ID_OBJETIVO = settings.park_id_objetivo
NAME_SIMILARITY_THRESHOLD = settings.name_similarity_threshold
LEAD_SYSTEM_START_DATE = date.fromisoformat(settings.lead_system_start_date)
