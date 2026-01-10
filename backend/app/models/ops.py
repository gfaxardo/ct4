from sqlalchemy import Column, Integer, DateTime, String, JSON, Enum, Date, Boolean, TypeDecorator, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
import enum
from app.db import Base


class RunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType(str, enum.Enum):
    IDENTITY_RUN = "identity_run"
    DRIVERS_INDEX_REFRESH = "drivers_index_refresh"
    SCOUT_ATTRIBUTION_REFRESH = "scout_attribution_refresh"


class JobTypeEnum(TypeDecorator):
    impl = ENUM
    cache_ok = True
    
    def __init__(self):
        super().__init__('identity_run', 'drivers_index_refresh', 'scout_attribution_refresh', name='jobtype', create_type=False)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, JobType):
            return value.value
        return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return JobType(value)
            except ValueError:
                return value
        return value


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = {"schema": "ops"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(RunStatus), default=RunStatus.RUNNING, nullable=False)
    stats = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    job_type = Column(JobTypeEnum(), nullable=True, server_default='identity_run')
    scope_date_from = Column(Date, nullable=True)
    scope_date_to = Column(Date, nullable=True)
    incremental = Column(Boolean, nullable=True, server_default='true')


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "ops"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    week_label = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    run_id = Column(Integer, ForeignKey("ops.ingestion_runs.id"), nullable=True)
