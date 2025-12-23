from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.sql import func
import enum
from app.db import Base


class AttributionConfidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    CONFLICT = "conflict"


class AttributionRule(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


class LeadEvent(Base):
    __tablename__ = "lead_events"
    __table_args__ = (
        {"schema": "observational"}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_table = Column(String, nullable=False)
    source_pk = Column(String, nullable=False)
    event_date = Column(Date, nullable=False)
    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key"), nullable=True)
    scout_id = Column(Integer, nullable=True)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LeadLedger(Base):
    __tablename__ = "lead_ledger"
    __table_args__ = (
        {"schema": "observational"}
    )

    person_key = Column(PGUUID(as_uuid=True), ForeignKey("canon.identity_registry.person_key"), primary_key=True)
    attributed_source = Column(String, nullable=True)
    attributed_scout_id = Column(Integer, nullable=True)
    attribution_rule = Column(String, nullable=True)
    attribution_score = Column(Numeric(5, 2), nullable=False)
    confidence_level = Column(Enum(AttributionConfidence), nullable=False)
    evidence_json = Column(JSONB, nullable=True)
    decision_status = Column(Enum(DecisionStatus), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
