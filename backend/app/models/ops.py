from sqlalchemy import Column, Integer, DateTime, String, JSON, Enum, Date, Boolean, TypeDecorator, Text, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
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


class IdentityMatchingJob(Base):
    __tablename__ = "identity_matching_jobs"
    __table_args__ = (
        CheckConstraint("source_type = 'cabinet'", name="chk_identity_matching_jobs_source_type"),
        CheckConstraint("status IN ('pending', 'matched', 'failed')", name="chk_identity_matching_jobs_status"),
        {"schema": "ops"}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    status = Column(String, nullable=False, server_default='pending')
    attempt_count = Column(Integer, nullable=False, server_default='0')
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    matched_person_key = Column(UUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key", ondelete="SET NULL"), nullable=True)
    fail_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CabinetKpiRedRecoveryQueue(Base):
    __tablename__ = "cabinet_kpi_red_recovery_queue"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'matched', 'failed')", name="chk_cabinet_kpi_red_recovery_queue_status"),
        {"schema": "ops"}
    )

    lead_source_pk = Column(String, primary_key=True, nullable=False)
    status = Column(String, nullable=False, server_default='pending')
    attempt_count = Column(Integer, nullable=False, server_default='0')
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    matched_person_key = Column(UUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key", ondelete="SET NULL"), nullable=True)
    fail_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)