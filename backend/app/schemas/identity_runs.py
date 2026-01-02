"""
Schemas Pydantic para listar y consultar corridas de identidad.

Basados en el modelo ops.ingestion_runs.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from datetime import datetime, date
import enum


class IngestionRunStatus(str, enum.Enum):
    """Estado de una corrida de ingesta."""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestionJobType(str, enum.Enum):
    """Tipo de job de ingesta."""
    IDENTITY_RUN = "identity_run"
    DRIVERS_INDEX_REFRESH = "drivers_index_refresh"


class IdentityRunStatsSource(BaseModel):
    """Estadísticas de una fuente de datos procesada."""
    processed: Optional[int] = None
    matched: Optional[int] = None
    unmatched: Optional[int] = None
    skipped: Optional[int] = None


class IdentityRunStats(BaseModel):
    """Estadísticas completas de una corrida de identidad.
    
    Parsea el campo JSON 'stats' de ops.ingestion_runs.
    Si faltan claves, se dejan como None.
    """
    cabinet_leads: Optional[IdentityRunStatsSource] = None
    scouting_daily: Optional[IdentityRunStatsSource] = None
    timings: Optional[Dict[str, float]] = None
    raw: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json(cls, stats_json: Optional[Dict[str, Any]]) -> Optional['IdentityRunStats']:
        """Construye IdentityRunStats desde el JSON de stats.
        
        Si stats_json es None, retorna None.
        Si faltan claves, se dejan como None.
        """
        if stats_json is None:
            return None

        # Parsear cabinet_leads
        cabinet_leads = None
        if "cabinet_leads" in stats_json and isinstance(stats_json["cabinet_leads"], dict):
            cabinet_leads = IdentityRunStatsSource(**stats_json["cabinet_leads"])

        # Parsear scouting_daily
        scouting_daily = None
        if "scouting_daily" in stats_json and isinstance(stats_json["scouting_daily"], dict):
            scouting_daily = IdentityRunStatsSource(**stats_json["scouting_daily"])

        # Parsear timings
        timings = None
        if "timings" in stats_json and isinstance(stats_json["timings"], dict):
            timings = stats_json["timings"]

        return cls(
            cabinet_leads=cabinet_leads,
            scouting_daily=scouting_daily,
            timings=timings,
            raw=stats_json  # Conservar todo el JSON completo
        )


class IdentityRunRow(BaseModel):
    """Una fila de corrida de identidad para listado."""
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: IngestionRunStatus
    job_type: IngestionJobType
    scope_date_from: Optional[date] = None
    scope_date_to: Optional[date] = None
    incremental: bool
    error_message: Optional[str] = None
    stats: Optional[IdentityRunStats] = None

    @field_validator('status', mode='before')
    @classmethod
    def parse_status(cls, v: Any) -> str:
        """Convierte RunStatus del modelo a string para IngestionRunStatus."""
        if hasattr(v, 'value'):
            return v.value
        if isinstance(v, str):
            return v
        return str(v)

    @field_validator('job_type', mode='before')
    @classmethod
    def parse_job_type(cls, v: Any) -> str:
        """Convierte JobType del modelo a string para IngestionJobType."""
        if hasattr(v, 'value'):
            return v.value
        if isinstance(v, str):
            return v
        return str(v)

    @field_validator('stats', mode='before')
    @classmethod
    def parse_stats(cls, v: Any) -> Optional[IdentityRunStats]:
        """Parsea el campo stats desde JSON."""
        if v is None:
            return None
        if isinstance(v, IdentityRunStats):
            return v
        if isinstance(v, dict):
            return IdentityRunStats.from_json(v)
        return None

    class Config:
        from_attributes = True


class IdentityRunsResponse(BaseModel):
    """Response para listado paginado de corridas de identidad."""
    items: list[IdentityRunRow]
    total: int
    limit: int
    offset: int

