"""
Schemas para el módulo de auditoría de origen.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from uuid import UUID
from app.models.canon import (
    OriginTag, OriginResolutionStatus, ViolationReason, 
    RecommendedAction, AlertType, AlertSeverity, AlertImpact
)


class IdentityOriginBase(BaseModel):
    origin_tag: OriginTag
    origin_source_id: str
    origin_confidence: float
    origin_created_at: datetime
    ruleset_version: str = "origin_rules_v1"
    evidence: Optional[Dict[str, Any]] = None
    decided_by: str = "system"
    notes: Optional[str] = None


class IdentityOriginCreate(IdentityOriginBase):
    person_key: UUID


class IdentityOriginUpdate(BaseModel):
    origin_tag: Optional[OriginTag] = None
    origin_source_id: Optional[str] = None
    origin_confidence: Optional[float] = None
    resolution_status: Optional[OriginResolutionStatus] = None
    notes: Optional[str] = None


class IdentityOriginResponse(IdentityOriginBase):
    person_key: UUID
    decided_at: datetime
    resolution_status: OriginResolutionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OriginAuditRow(BaseModel):
    person_key: UUID
    driver_id: Optional[str] = None
    origin_tag: Optional[str] = None
    origin_source_id: Optional[str] = None
    origin_confidence: Optional[float] = None
    origin_created_at: Optional[datetime] = None
    ruleset_version: Optional[str] = None
    origin_evidence: Optional[Dict[str, Any]] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    resolution_status: Optional[str] = None
    notes: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    driver_linked_at: Optional[datetime] = None
    has_lead_links: bool = False
    links_summary: Optional[List[Dict[str, Any]]] = None
    violation_flag: bool = False
    violation_reason: Optional[str] = None
    recommended_action: Optional[str] = None


class OriginAlertRow(BaseModel):
    alert_id: int
    person_key: UUID
    driver_id: Optional[str] = None
    alert_type: str
    violation_reason: Optional[str] = None
    recommended_action: Optional[str] = None
    severity: str
    impact: str
    origin_tag: Optional[str] = None
    origin_confidence: Optional[float] = None
    first_seen_at: Optional[datetime] = None
    first_detected_at: Optional[datetime] = None
    last_detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    muted_until: Optional[datetime] = None
    alert_notes: Optional[str] = None
    is_resolved_or_muted: bool = False
    resolution_status: Optional[str] = None


class OriginAuditListResponse(BaseModel):
    items: List[OriginAuditRow]
    total: int
    skip: int
    limit: int


class OriginAlertListResponse(BaseModel):
    items: List[OriginAlertRow]
    total: int
    skip: int
    limit: int


class ResolveOriginRequest(BaseModel):
    resolution_status: OriginResolutionStatus
    notes: Optional[str] = None
    origin_tag: Optional[OriginTag] = None
    origin_source_id: Optional[str] = None


class MarkLegacyRequest(BaseModel):
    notes: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    resolved_by: str
    notes: Optional[str] = None


class MuteAlertRequest(BaseModel):
    muted_until: datetime
    notes: Optional[str] = None


class BatchResolveRequest(BaseModel):
    person_keys: List[UUID]
    resolution_status: OriginResolutionStatus
    notes: Optional[str] = None


class OriginAuditStats(BaseModel):
    total_persons: int
    persons_with_violations: int
    violations_by_reason: Dict[str, int]
    violations_by_severity: Dict[str, int]
    resolution_status_distribution: Dict[str, int]
    alerts_by_type: Dict[str, int]
    alerts_by_severity: Dict[str, int]

