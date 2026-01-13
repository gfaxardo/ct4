from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum, ForeignKey, UniqueConstraint, Numeric, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ENUM
from sqlalchemy.sql import func
import uuid
import enum
from app.db import Base


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class UnmatchedStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class OriginTag(str, enum.Enum):
    CABINET_LEAD = "cabinet_lead"
    SCOUT_REGISTRATION = "scout_registration"
    MIGRATION = "migration"
    LEGACY_EXTERNAL = "legacy_external"
    
    def __str__(self):
        return self.value


class DecidedBy(str, enum.Enum):
    SYSTEM = "system"
    MANUAL = "manual"


class OriginResolutionStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    RESOLVED_AUTO = "resolved_auto"
    RESOLVED_MANUAL = "resolved_manual"
    MARKED_LEGACY = "marked_legacy"
    DISCARDED = "discarded"


class ViolationReason(str, enum.Enum):
    MISSING_ORIGIN = "missing_origin"
    MULTIPLE_ORIGINS = "multiple_origins"
    LATE_ORIGIN_LINK = "late_origin_link"
    ORPHAN_LEAD = "orphan_lead"
    LEGACY_DRIVER_UNCLASSIFIED = "legacy_driver_unclassified"


class RecommendedAction(str, enum.Enum):
    AUTO_LINK = "auto_link"
    MANUAL_REVIEW = "manual_review"
    MARK_LEGACY = "mark_legacy"
    DISCARD = "discard"


class AlertType(str, enum.Enum):
    MISSING_ORIGIN = "missing_origin"
    MULTIPLE_ORIGINS = "multiple_origins"
    LEGACY_UNCLASSIFIED = "legacy_unclassified"
    ORPHAN_LEAD = "orphan_lead"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertImpact(str, enum.Enum):
    EXPORT = "export"
    COLLECTION = "collection"
    REPORTING = "reporting"
    NONE = "none"


class OrphanDetectedReason(str, enum.Enum):
    NO_LEAD_NO_EVENTS = "no_lead_no_events"
    NO_LEAD_HAS_EVENTS_REPAIR_FAILED = "no_lead_has_events_repair_failed"
    LEGACY_DRIVER_WITHOUT_ORIGIN = "legacy_driver_without_origin"
    MANUAL_DETECTION = "manual_detection"


class OrphanStatus(str, enum.Enum):
    QUARANTINED = "quarantined"
    RESOLVED_RELINKED = "resolved_relinked"
    RESOLVED_CREATED_LEAD = "resolved_created_lead"
    PURGED = "purged"


class OrphanDetectedReasonEnum(TypeDecorator):
    """TypeDecorator para manejar OrphanDetectedReason enum correctamente"""
    impl = ENUM
    cache_ok = True
    
    def __init__(self):
        super().__init__(
            'no_lead_no_events', 
            'no_lead_has_events_repair_failed', 
            'legacy_driver_without_origin', 
            'manual_detection', 
            name='orphan_detected_reason', 
            create_type=False
        )
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, OrphanDetectedReason):
            return value.value
        return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return OrphanDetectedReason(value)
            except ValueError:
                return value
        return value


class OrphanStatusEnum(TypeDecorator):
    """TypeDecorator para manejar OrphanStatus enum correctamente"""
    impl = ENUM
    cache_ok = True
    
    def __init__(self):
        super().__init__(
            'quarantined',
            'resolved_relinked',
            'resolved_created_lead',
            'purged',
            name='orphan_status',
            create_type=False
        )
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, OrphanStatus):
            return value.value
        return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return OrphanStatus(value)
            except ValueError:
                return value
        return value


class IdentityRegistry(Base):
    __tablename__ = "identity_registry"
    __table_args__ = {"schema": "canon"}

    person_key = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    confidence_level = Column(Enum(ConfidenceLevel), nullable=False)
    primary_phone = Column(String, nullable=True)
    primary_document = Column(String, nullable=True)
    primary_license = Column(String, nullable=True)
    primary_full_name = Column(String, nullable=True)
    flags = Column(JSONB, nullable=True)


class IdentityLink(Base):
    __tablename__ = "identity_links"
    __table_args__ = (
        UniqueConstraint("source_table", "source_pk", name="uq_identity_links_source"),
        {"schema": "canon"}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key"), nullable=False)
    source_table = Column(String, nullable=False)
    source_pk = Column(String, nullable=False)
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    match_rule = Column(String, nullable=False)
    match_score = Column(Integer, nullable=False)
    confidence_level = Column(Enum(ConfidenceLevel), nullable=False)
    evidence = Column(JSONB, nullable=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    run_id = Column(Integer, ForeignKey("ops.ingestion_runs.id"), nullable=True)


class IdentityUnmatched(Base):
    __tablename__ = "identity_unmatched"
    __table_args__ = (
        UniqueConstraint("source_table", "source_pk", name="uq_identity_unmatched_source"),
        {"schema": "canon"}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_table = Column(String, nullable=False)
    source_pk = Column(String, nullable=False)
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    reason_code = Column(String, nullable=False)
    details = Column(JSONB, nullable=True)
    candidates_preview = Column(JSONB, nullable=True)
    status = Column(Enum(UnmatchedStatus), default=UnmatchedStatus.OPEN, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    run_id = Column(Integer, ForeignKey("ops.ingestion_runs.id"), nullable=True)


class IdentityOrigin(Base):
    __tablename__ = "identity_origin"
    __table_args__ = {"schema": "canon"}

    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key", ondelete="CASCADE"), primary_key=True)
    origin_tag = Column(Enum(OriginTag), nullable=False)
    origin_source_id = Column(String, nullable=False)
    origin_confidence = Column(Numeric(precision=5, scale=2), nullable=False)
    origin_created_at = Column(DateTime(timezone=True), nullable=False)
    ruleset_version = Column(String, nullable=False, server_default="origin_rules_v1")
    evidence = Column(JSONB, nullable=True)
    decided_by = Column(Enum(DecidedBy), nullable=False, server_default=DecidedBy.SYSTEM.value)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolution_status = Column(Enum(OriginResolutionStatus), nullable=False, server_default=OriginResolutionStatus.PENDING_REVIEW.value)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IdentityOriginHistory(Base):
    __tablename__ = "identity_origin_history"
    __table_args__ = {"schema": "canon"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key", ondelete="CASCADE"), nullable=False)
    origin_tag_old = Column(String, nullable=True)
    origin_tag_new = Column(String, nullable=True)
    origin_source_id_old = Column(String, nullable=True)
    origin_source_id_new = Column(String, nullable=True)
    origin_confidence_old = Column(Numeric(precision=5, scale=2), nullable=True)
    origin_confidence_new = Column(Numeric(precision=5, scale=2), nullable=True)
    resolution_status_old = Column(String, nullable=True)
    resolution_status_new = Column(String, nullable=True)
    ruleset_version_old = Column(String, nullable=True)
    ruleset_version_new = Column(String, nullable=True)
    changed_by = Column(String, nullable=False)
    change_reason = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IdentityOriginAlertState(Base):
    __tablename__ = "identity_origin_alert_state"
    __table_args__ = (
        UniqueConstraint("person_key", "alert_type", name="uq_identity_origin_alert_state"),
        {"schema": "ops"}
    )

    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key", ondelete="CASCADE"), primary_key=True)
    alert_type = Column(Enum(AlertType), primary_key=True)
    first_detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String, nullable=True)
    muted_until = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DriverOrphanQuarantine(Base):
    __tablename__ = "driver_orphan_quarantine"
    __table_args__ = {"schema": "canon"}

    driver_id = Column(String, primary_key=True)
    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key", ondelete="SET NULL"), nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    detected_reason = Column(OrphanDetectedReasonEnum(), nullable=False)
    creation_rule = Column(String, nullable=True)
    evidence_json = Column(JSONB, nullable=True)
    status = Column(OrphanStatusEnum(), server_default='quarantined', nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

