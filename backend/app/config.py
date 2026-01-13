"""
Application configuration using Pydantic Settings.

All sensitive values should be provided via environment variables or .env file.
"""
import os
from datetime import date
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        database_url: PostgreSQL connection string
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        park_id_objetivo: Target park ID for filtering
        name_similarity_threshold: Threshold for name matching (0-1)
        admin_token: Token for admin authentication
        lead_system_start_date: ISO date string for legacy detection cutoff
    """
    # Database connection
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
    )
    
    # Logging
    log_level: str = "INFO"
    
    # Business configuration
    park_id_objetivo: str = "08e20910d81d42658d4334d3f6d10ac0"
    name_similarity_threshold: float = 0.66
    
    # Security
    admin_token: str = ""
    
    # Date configuration for legacy detection
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
