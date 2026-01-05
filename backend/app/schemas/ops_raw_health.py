"""
Schemas Pydantic para consultar salud de datos RAW.

Basados en las vistas:
- ops.v_data_health_status
- ops.v_data_freshness_status
- ops.v_data_ingestion_daily
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class RawDataHealthStatusRow(BaseModel):
    """Fila de salud de datos por fuente.
    
    Basado en ops.v_data_health_status.
    """
    source_name: str
    source_type: Optional[str] = None
    max_business_date: Optional[date] = None
    business_days_lag: Optional[int] = None
    max_ingestion_ts: Optional[datetime] = None
    ingestion_lag_interval: Optional[str] = None  # PostgreSQL interval como string
    rows_business_yesterday: Optional[int] = None
    rows_business_today: Optional[int] = None
    rows_ingested_yesterday: Optional[int] = None
    rows_ingested_today: Optional[int] = None
    health_status: Optional[str] = None

    class Config:
        from_attributes = True


class RawDataFreshnessStatusRow(BaseModel):
    """Fila de frescura de datos por fuente.
    
    Basado en ops.v_data_freshness_status.
    """
    source_name: str
    max_business_date: Optional[date] = None
    business_days_lag: Optional[int] = None
    max_ingestion_ts: Optional[datetime] = None
    ingestion_lag_interval: Optional[str] = None  # PostgreSQL interval como string
    rows_business_yesterday: Optional[int] = None
    rows_business_today: Optional[int] = None
    rows_ingested_yesterday: Optional[int] = None
    rows_ingested_today: Optional[int] = None

    class Config:
        from_attributes = True


class RawDataIngestionDailyRow(BaseModel):
    """Fila de ingesta diaria por fuente.
    
    Basado en ops.v_data_ingestion_daily.
    """
    source_name: str
    metric_type: str  # 'business' o 'ingestion'
    metric_date: date
    rows_count: int

    class Config:
        from_attributes = True


# Response schemas con paginación
class RawDataHealthStatusResponse(BaseModel):
    """Response paginado para status de salud de datos RAW."""
    items: list[RawDataHealthStatusRow]
    total: int
    limit: int
    offset: int


class RawDataFreshnessStatusResponse(BaseModel):
    """Response paginado para status de frescura de datos RAW."""
    items: list[RawDataFreshnessStatusRow]
    total: int
    limit: int
    offset: int


class RawDataIngestionDailyResponse(BaseModel):
    """Response paginado para ingesta diaria de datos RAW."""
    items: list[RawDataIngestionDailyRow]
    total: int
    limit: int
    offset: int




