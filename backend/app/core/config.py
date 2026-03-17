"""
Configuración de la aplicación (Pydantic Settings).

Valores sensibles vía variables de entorno o .env.
Acepta DATABASE_URL o, si no está definida, construye la URL desde DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.
"""
import os
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Cargar .env para que default_factory pueda leer DB_* si no hay DATABASE_URL
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def _build_database_url() -> str:
    """Construye la URL desde DATABASE_URL o desde DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD."""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        return url
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    raw = (os.getenv("DB_PASSWORD") or "").strip().strip('"').strip("'")
    if host and name and user:
        safe = quote_plus(raw)
        return f"postgresql://{user}:{safe}@{host}:{port}/{name}"
    return "postgresql://localhost:5432/ct4"


class Settings(BaseSettings):
    """
    Configuración cargada desde variables de entorno o .env.
    Base de datos: DATABASE_URL o (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
    """
    database_url: str = Field(default_factory=_build_database_url)
    db_host: str | None = None
    db_port: str = "5432"
    db_name: str | None = None
    db_user: str | None = None
    db_password: str = ""

    log_level: str = "INFO"
    environment: str = "development"
    cors_origins: str = "*"
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
