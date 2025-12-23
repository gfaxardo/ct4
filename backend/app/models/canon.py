from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.schema import CreateSchema
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



