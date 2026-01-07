from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import date

from app.db import get_db
from app.schemas.attribution import (
    LeadEvent, LeadLedger, PopulateEventsRequest, ProcessLedgerRequest, AttributionStats
)
from app.services.lead_attribution import LeadAttributionService
from app.models.observational import LeadEvent as LeadEventModel, LeadLedger as LeadLedgerModel

router = APIRouter()


@router.post("/populate-events", response_model=dict)
def populate_events(
    request: PopulateEventsRequest,
    db: Session = Depends(get_db)
):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Iniciando populate_events. source_tables={request.source_tables}, date_from={request.date_from}, date_to={request.date_to}")
    
    service = LeadAttributionService(db)
    stats = {"scouting": {}, "cabinet": {}, "migrations": {}}
    
    source_tables = request.source_tables or ["module_ct_scouting_daily", "module_ct_cabinet_leads", "module_ct_migrations"]
    
    if "module_ct_scouting_daily" in source_tables:
        logger.info("Procesando module_ct_scouting_daily...")
        stats["scouting"] = service.populate_events_from_scouting(
            date_from=request.date_from,
            date_to=request.date_to,
            run_id=None  # TODO: obtener run_id del request si está disponible
        )
        logger.info(f"Scouting completado: {stats['scouting']}")
    
    if "module_ct_cabinet_leads" in source_tables:
        logger.info("Procesando module_ct_cabinet_leads...")
        stats["cabinet"] = service.populate_events_from_cabinet(
            date_from=request.date_from,
            date_to=request.date_to
        )
        logger.info(f"Cabinet completado: {stats['cabinet']}")
    
    if "module_ct_migrations" in source_tables:
        logger.info("Procesando module_ct_migrations...")
        migrations_stats = service.populate_events_from_migrations(
            date_from=request.date_from,
            date_to=request.date_to,
            run_id=None  # TODO: obtener run_id del request si está disponible
        )
        # Mapear métricas al formato requerido
        stats["migrations"] = {
            "migrations_total": migrations_stats.get("processed", 0),
            "migrations_inserted": migrations_stats.get("created", 0),
            "migrations_errors": migrations_stats.get("errors", 0)
        }
        logger.info(f"Migrations completado: {stats['migrations']}")
    
    logger.info("populate_events completado exitosamente")
    
    return {
        "status": "completed",
        "stats": stats
    }


@router.post("/process-ledger", response_model=dict)
def process_ledger(
    request: ProcessLedgerRequest,
    db: Session = Depends(get_db)
):
    service = LeadAttributionService(db)
    stats = service.process_ledger(
        date_from=request.date_from,
        date_to=request.date_to,
        source_tables=request.source_tables,
        person_keys=request.person_keys
    )
    
    return {
        "status": "completed",
        "stats": stats
    }


@router.get("/ledger/{person_key}", response_model=LeadLedger)
def get_ledger_entry(
    person_key: UUID,
    db: Session = Depends(get_db)
):
    entry = db.query(LeadLedgerModel).filter(
        LeadLedgerModel.person_key == person_key
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada de ledger no encontrada")
    
    return entry


@router.get("/events", response_model=List[LeadEvent])
def list_events(
    person_key: Optional[UUID] = Query(None, description="Filtrar por person_key"),
    source_table: Optional[str] = Query(None, description="Filtrar por source_table"),
    scout_id: Optional[int] = Query(None, description="Filtrar por scout_id"),
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(LeadEventModel)
    
    if person_key:
        query = query.filter(LeadEventModel.person_key == person_key)
    
    if source_table:
        query = query.filter(LeadEventModel.source_table == source_table)
    
    if scout_id is not None:
        query = query.filter(LeadEventModel.scout_id == scout_id)
    
    if date_from:
        query = query.filter(LeadEventModel.event_date >= date_from)
    
    if date_to:
        query = query.filter(LeadEventModel.event_date <= date_to)
    
    events = query.order_by(LeadEventModel.event_date.desc()).offset(skip).limit(limit).all()
    
    return events


@router.get("/stats", response_model=AttributionStats)
def get_stats(db: Session = Depends(get_db)):
    total_events = db.query(LeadEventModel).count()
    events_with_person_key = db.query(LeadEventModel).filter(
        LeadEventModel.person_key.isnot(None)
    ).count()
    events_without_person_key = total_events - events_with_person_key
    
    total_ledger_entries = db.query(LeadLedgerModel).count()
    assigned_count = db.query(LeadLedgerModel).filter(
        LeadLedgerModel.decision_status == "assigned"
    ).count()
    unassigned_count = db.query(LeadLedgerModel).filter(
        LeadLedgerModel.decision_status == "unassigned"
    ).count()
    conflict_count = db.query(LeadLedgerModel).filter(
        LeadLedgerModel.decision_status == "conflict"
    ).count()
    
    return AttributionStats(
        total_events=total_events,
        events_with_person_key=events_with_person_key,
        events_without_person_key=events_without_person_key,
        total_ledger_entries=total_ledger_entries,
        assigned_count=assigned_count,
        unassigned_count=unassigned_count,
        conflict_count=conflict_count
    )






























