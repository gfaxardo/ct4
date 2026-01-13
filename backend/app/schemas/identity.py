"""
Identity-related Pydantic schemas for API validation.

Defines schemas for IdentityRegistry, IdentityLink, and related endpoints.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.canon import ConfidenceLevel, UnmatchedStatus


class IdentityRegistryBase(BaseModel):
    confidence_level: ConfidenceLevel
    primary_phone: Optional[str] = None
    primary_document: Optional[str] = None
    primary_license: Optional[str] = None
    primary_full_name: Optional[str] = None
    flags: Optional[Dict[str, Any]] = None


class IdentityRegistry(IdentityRegistryBase):
    person_key: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IdentityLinkBase(BaseModel):
    source_table: str
    source_pk: str
    snapshot_date: datetime
    match_rule: str
    match_score: int
    confidence_level: ConfidenceLevel
    evidence: Optional[Dict[str, Any]] = None


class IdentityLink(IdentityLinkBase):
    id: int
    person_key: UUID
    linked_at: datetime
    run_id: Optional[int] = None

    class Config:
        from_attributes = True


class IdentityUnmatchedBase(BaseModel):
    source_table: str
    source_pk: str
    snapshot_date: datetime
    reason_code: str
    details: Optional[Dict[str, Any]] = None
    candidates_preview: Optional[Dict[str, Any]] = None
    status: UnmatchedStatus = UnmatchedStatus.OPEN


class IdentityUnmatched(IdentityUnmatchedBase):
    id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
    run_id: Optional[int] = None

    class Config:
        from_attributes = True


class PersonDetail(BaseModel):
    person: IdentityRegistry
    links: list[IdentityLink]
    driver_links: Optional[list[IdentityLink]] = None
    has_driver_conversion: bool = False


class UnmatchedResolveRequest(BaseModel):
    person_key: UUID


class StatsResponse(BaseModel):
    total_persons: int
    total_unmatched: int
    total_links: int
    drivers_links: Optional[int] = 0
    conversion_rate: Optional[float] = 0.0


class PersonsBySourceResponse(BaseModel):
    total_persons: int
    links_by_source: Dict[str, int]
    persons_with_cabinet_leads: int
    persons_with_scouting_daily: int
    persons_with_drivers: int
    persons_only_drivers: int
    persons_with_cabinet_or_scouting: int


class DriversWithoutLeadsAnalysis(BaseModel):
    total_drivers_without_leads: int  # Total incluyendo quarantined
    drivers_quarantined_count: int  # Drivers en cuarentena
    drivers_without_leads_operativos: int  # Total - quarantined (drivers operativos sin lead)
    by_match_rule: Dict[str, int]
    drivers_with_lead_events: int
    drivers_without_lead_events: int
    missing_links_by_source: Dict[str, int]
    sample_drivers: List[Dict[str, Any]]
    quarantine_breakdown: Dict[str, int] = {}  # breakdown por detected_reason


class WeeklyData(BaseModel):
    week_start: str
    week_label: str
    source_table: str
    matched: int
    unmatched: int
    processed_total: int
    match_rate: float
    matched_by_rule: Dict[str, int]
    matched_by_confidence: Dict[str, int]
    unmatched_by_reason: Dict[str, int]
    top_missing_keys: list[Dict[str, Any]]


class WeeklyTrend(BaseModel):
    week_label: str
    source_table: Optional[str]
    delta_match_rate: Optional[float]
    delta_matched: Optional[int]
    delta_unmatched: Optional[int]
    current_match_rate: float
    previous_match_rate: Optional[float]


class ScoutingKPIData(BaseModel):
    week_label: str
    source_table: str
    processed_scouting: int
    candidates_detected: int
    candidate_rate: float
    high_confidence_candidates: int
    avg_time_to_match_days: Optional[float]


class RunReportResponse(BaseModel):
    run: Dict[str, Any]
    counts_by_source_table: Dict[str, Dict[str, int]]
    matched_breakdown: Dict[str, Dict[str, int]]
    unmatched_breakdown: Dict[str, Any]
    samples: Dict[str, list]
    weekly: Optional[list[WeeklyData]] = None
    weekly_trend: Optional[list[WeeklyTrend]] = None
    available_event_weeks: Optional[list[str]] = None
    scouting_kpis: Optional[list[ScoutingKPIData]] = None


class MetricsScope(BaseModel):
    run_id: Optional[int] = None
    source_table: Optional[str] = None
    event_date_from: Optional[date] = None
    event_date_to: Optional[date] = None
    mode: Literal["summary", "weekly", "breakdowns"] = "summary"


class MetricsResponse(BaseModel):
    scope: MetricsScope
    totals: Dict[str, Any]  # total_processed, matched, unmatched, match_rate
    weekly: Optional[List[WeeklyData]] = None
    weekly_trend: Optional[List[WeeklyTrend]] = None
    available_event_weeks: Optional[List[str]] = None
    breakdowns: Optional[Dict[str, Any]] = None


# Schemas para Orphans / Cuarentena
class OrphanDriver(BaseModel):
    driver_id: str
    person_key: Optional[UUID] = None
    detected_at: datetime
    detected_reason: str
    creation_rule: Optional[str] = None
    evidence_json: Optional[Dict[str, Any]] = None
    status: str
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    primary_phone: Optional[str] = None
    primary_license: Optional[str] = None
    primary_full_name: Optional[str] = None
    driver_links_count: int = 0
    lead_events_count: int = 0

    class Config:
        from_attributes = True


class OrphansListResponse(BaseModel):
    orphans: List[OrphanDriver]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrphansMetricsResponse(BaseModel):
    total_orphans: int
    by_status: Dict[str, int]
    by_reason: Dict[str, int]
    quarantined: int
    resolved_relinked: int
    resolved_created_lead: int
    purged: int
    with_lead_events: int
    without_lead_events: int
    last_updated_at: Optional[datetime] = None


class RunFixResponse(BaseModel):
    dry_run: bool
    timestamp: str
    stats: Dict[str, Any]
    drivers: List[Dict[str, Any]]
    report_path: Optional[str] = None

