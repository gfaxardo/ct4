from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID


class LeadEventBase(BaseModel):
    source_table: str
    source_pk: str
    event_date: date
    person_key: Optional[UUID] = None
    scout_id: Optional[int] = None
    payload_json: Optional[Dict[str, Any]] = None


class LeadEventCreate(LeadEventBase):
    pass


class LeadEvent(LeadEventBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LeadLedgerBase(BaseModel):
    attributed_source: Optional[str] = None
    attributed_scout_id: Optional[int] = None
    attribution_rule: str
    attribution_score: float
    confidence_level: str
    evidence_json: Optional[Dict[str, Any]] = None
    decision_status: str


class LeadLedger(LeadLedgerBase):
    person_key: UUID
    updated_at: datetime

    class Config:
        from_attributes = True


class PopulateEventsRequest(BaseModel):
    source_tables: Optional[list[str]] = Field(None, description="Tablas a procesar. Si None, procesa todas")
    date_from: Optional[date] = Field(None, description="Fecha inicio del scope")
    date_to: Optional[date] = Field(None, description="Fecha fin del scope")


class ProcessLedgerRequest(BaseModel):
    person_keys: Optional[list[UUID]] = Field(None, description="Personas específicas a procesar. Si None, procesa todas")
    date_from: Optional[date] = Field(None, description="Fecha inicio del rango de eventos a procesar")
    date_to: Optional[date] = Field(None, description="Fecha fin del rango de eventos a procesar")
    source_tables: Optional[list[str]] = Field(None, description="Tablas fuente a considerar. Si None, usa ['module_ct_scouting_daily', 'module_ct_cabinet_leads', 'module_ct_migrations']")


class AttributionStats(BaseModel):
    total_events: int
    events_with_person_key: int
    events_without_person_key: int
    total_ledger_entries: int
    assigned_count: int
    unassigned_count: int
    conflict_count: int

