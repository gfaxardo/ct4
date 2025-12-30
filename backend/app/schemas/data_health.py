from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class DataFreshnessStatus(BaseModel):
    source_name: str
    max_business_date: Optional[date] = None
    business_days_lag: Optional[int] = None
    max_ingestion_ts: Optional[datetime] = None
    ingestion_lag_interval: Optional[str] = None  # Intervalo como string (ej: "2 hours")
    rows_business_yesterday: int = 0
    rows_business_today: int = 0
    rows_ingested_yesterday: int = 0
    rows_ingested_today: int = 0

    class Config:
        from_attributes = True


class DataHealthStatus(DataFreshnessStatus):
    source_type: Optional[str] = None  # 'activity', 'ledger', 'upstream', 'ct_ingest', 'master'
    health_status: str  # 'GREEN_OK', 'YELLOW_INGESTION_1D', 'YELLOW_BUSINESS_LAG', 'RED_INGESTION_STALE', 'RED_NO_INGESTION_2D', 'RED_NO_DATA'

    class Config:
        from_attributes = True


class DataIngestionDaily(BaseModel):
    source_name: str
    metric_type: str  # 'business' o 'ingestion'
    metric_date: date
    rows_count: int

    class Config:
        from_attributes = True


class DataHealthResponse(BaseModel):
    freshness_status: List[DataFreshnessStatus]
    health_status: List[DataHealthStatus]
    ingestion_daily: List[DataIngestionDaily]

