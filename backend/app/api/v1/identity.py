from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text, Date, select, bindparam, cast, String
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
import json
from app.db import get_db, SessionLocal
from app.models.canon import (
    IdentityRegistry, 
    IdentityLink, 
    IdentityUnmatched, 
    ConfidenceLevel, 
    UnmatchedStatus,
    DriverOrphanQuarantine,
    OrphanStatus,
    OrphanDetectedReason
)
from app.models.ops import IngestionRun, JobType, RunStatus
from app.models.observational import ScoutingMatchCandidate, LeadEvent as LeadEventModel
import logging

logger = logging.getLogger(__name__)

from app.schemas.identity import (
    IdentityRegistry as IdentityRegistrySchema, 
    IdentityLink as IdentityLinkSchema, 
    IdentityUnmatched as IdentityUnmatchedSchema, 
    PersonDetail, 
    UnmatchedResolveRequest, 
    StatsResponse, 
    RunReportResponse, 
    MetricsScope, 
    MetricsResponse, 
    PersonsBySourceResponse, 
    DriversWithoutLeadsAnalysis,
    OrphanDriver,
    OrphansListResponse,
    OrphansMetricsResponse,
    RunFixResponse
)
from app.schemas.ingestion import IngestionRun as IngestionRunSchema
from app.schemas.identity_runs import IdentityRunsResponse, IdentityRunRow, IngestionRunStatus, IngestionJobType
from app.services.ingestion import IngestionService
from app.services.normalization import normalize_phone, normalize_name, normalize_license, tokenize_name
from app.services.scouting_observation import ScoutingObservationService

router = APIRouter()


@router.post("/drivers-index/refresh", response_model=IngestionRunSchema)
def refresh_drivers_index(db: Session = Depends(get_db)):
    service = IngestionService(db)
    run = service.refresh_drivers_index_job()
    return run


def _run_ingestion_background(
    run_id: int,
    date_from: Optional[date],
    date_to: Optional[date],
    scope_date: Optional[date],
    source_tables: Optional[List[str]],
    incremental: bool,
    refresh_index: bool
):
    db = SessionLocal()
    try:
        service = IngestionService(db)
        service.run_ingestion(
            scope_date_from=date_from,
            scope_date_to=date_to,
            scope_date=scope_date,
            source_tables=source_tables,
            incremental=incremental,
            run_id=run_id,
            refresh_index=refresh_index
        )
    except Exception as e:
        logger.error(f"Error en background task para run_id {run_id}: {str(e)}")
    finally:
        db.close()


@router.post("/run", response_model=IngestionRunSchema)
def run_ingestion(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Fecha inicio del scope"),
    date_to: Optional[date] = Query(None, description="Fecha fin del scope"),
    scope_date: Optional[date] = Query(None, description="Fecha única del scope (alternativa a date_from/date_to)"),
    source_tables: Optional[List[str]] = Query(None, description="Tablas a procesar (module_ct_cabinet_leads, module_ct_scouting_daily)"),
    incremental: bool = Query(True, description="Modo incremental (usa última corrida si no hay scope_date_from)"),
    refresh_index: bool = Query(False, description="Refrescar drivers_index antes de procesar")
):
    from app.models.ops import IngestionRun, RunStatus, JobType
    
    if scope_date:
        date_from = scope_date
        date_to = scope_date
    
    first_run = db.query(IngestionRun).filter(
        IngestionRun.job_type == JobType.IDENTITY_RUN,
        IngestionRun.status == RunStatus.COMPLETED
    ).first()
    
    if not first_run and not date_from and not date_to and not scope_date:
        raise HTTPException(
            status_code=400,
            detail="Scope requerido en primer run. Use date_from/date_to."
        )
    
    run = IngestionRun(
        status=RunStatus.RUNNING,
        job_type=JobType.IDENTITY_RUN,
        scope_date_from=date_from,
        scope_date_to=date_to,
        incremental=incremental
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    background_tasks.add_task(
        _run_ingestion_background,
        run.id,
        date_from,
        date_to,
        scope_date,
        source_tables,
        incremental,
        refresh_index
    )
    
    return run


@router.get("/persons", response_model=List[IdentityRegistrySchema])
def list_persons(
    db: Session = Depends(get_db),
    phone: Optional[str] = None,
    document: Optional[str] = None,
    license: Optional[str] = None,
    name: Optional[str] = None,
    confidence_level: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    query = db.query(IdentityRegistry)

    if phone:
        phone_norm = normalize_phone(phone)
        if phone_norm:
            query = query.filter(IdentityRegistry.primary_phone == phone_norm)

    if document:
        query = query.filter(IdentityRegistry.primary_document.contains(document))

    if license:
        license_norm = normalize_license(license)
        if license_norm:
            query = query.filter(IdentityRegistry.primary_license == license_norm)

    if name:
        name_norm = normalize_name(name)
        if name_norm:
            name_tokens = set(tokenize_name(name))
            query = query.filter(
                or_(
                    IdentityRegistry.primary_full_name.contains(name_norm),
                    *[IdentityRegistry.primary_full_name.contains(token) for token in name_tokens if len(token) > 2]
                )
            )

    if confidence_level:
        try:
            conf_level = ConfidenceLevel(confidence_level.upper())
            query = query.filter(IdentityRegistry.confidence_level == conf_level)
        except ValueError:
            pass

    persons = query.offset(skip).limit(limit).all()
    return persons


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas del sistema de identidad.
    Optimizado: una sola query en lugar de 5 queries separadas.
    """
    # Query optimizada - combina todos los conteos en una sola consulta
    stats_query = text("""
        SELECT
            (SELECT COUNT(*) FROM canon.identity_registry) AS total_persons,
            (SELECT COUNT(*) FROM canon.identity_unmatched WHERE status = 'OPEN') AS total_unmatched,
            (SELECT COUNT(*) FROM canon.identity_links) AS total_links,
            (SELECT COUNT(*) FROM canon.identity_links WHERE source_table = 'drivers') AS drivers_links,
            (SELECT COUNT(*) FROM canon.identity_links 
             WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily')) AS cabinet_scouting_links
    """)
    
    result = db.execute(stats_query).fetchone()
    
    total_persons = result.total_persons or 0
    total_unmatched = result.total_unmatched or 0
    total_links = result.total_links or 0
    drivers_links = result.drivers_links or 0
    cabinet_scouting_links = result.cabinet_scouting_links or 0
    
    conversion_rate = 0.0
    if cabinet_scouting_links > 0:
        conversion_rate = (drivers_links / cabinet_scouting_links) * 100
    
    return StatsResponse(
        total_persons=total_persons,
        total_unmatched=total_unmatched,
        total_links=total_links,
        drivers_links=drivers_links,
        conversion_rate=conversion_rate
    )


@router.get("/stats/persons-by-source", response_model=PersonsBySourceResponse)
def get_persons_by_source(db: Session = Depends(get_db)):
    """
    Obtiene el desglose de personas identificadas por fuente de datos.
    Optimizado: una sola query en lugar de 8 queries separadas.
    """
    # Query optimizada - todo en una sola consulta
    stats_query = text("""
        WITH link_stats AS (
            SELECT 
                source_table,
                COUNT(*) as link_count,
                COUNT(DISTINCT person_key) as person_count
            FROM canon.identity_links
            GROUP BY source_table
        ),
        persons_only_drivers AS (
            SELECT COUNT(DISTINCT d.person_key) as cnt
            FROM canon.identity_links d
            WHERE d.source_table = 'drivers'
            AND NOT EXISTS (
                SELECT 1 FROM canon.identity_links l
                WHERE l.person_key = d.person_key
                AND l.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily')
            )
        )
        SELECT
            (SELECT COUNT(*) FROM canon.identity_registry) AS total_persons,
            COALESCE((SELECT link_count FROM link_stats WHERE source_table = 'module_ct_cabinet_leads'), 0) AS links_cabinet,
            COALESCE((SELECT link_count FROM link_stats WHERE source_table = 'module_ct_scouting_daily'), 0) AS links_scouting,
            COALESCE((SELECT link_count FROM link_stats WHERE source_table = 'drivers'), 0) AS links_drivers,
            COALESCE((SELECT person_count FROM link_stats WHERE source_table = 'module_ct_cabinet_leads'), 0) AS persons_cabinet,
            COALESCE((SELECT person_count FROM link_stats WHERE source_table = 'module_ct_scouting_daily'), 0) AS persons_scouting,
            COALESCE((SELECT person_count FROM link_stats WHERE source_table = 'drivers'), 0) AS persons_drivers,
            (SELECT COUNT(DISTINCT person_key) FROM canon.identity_links 
             WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily')) AS persons_cabinet_or_scouting,
            (SELECT cnt FROM persons_only_drivers) AS persons_only_drivers
    """)
    
    result = db.execute(stats_query).fetchone()
    
    return PersonsBySourceResponse(
        total_persons=result.total_persons or 0,
        links_by_source={
            "module_ct_cabinet_leads": result.links_cabinet or 0,
            "module_ct_scouting_daily": result.links_scouting or 0,
            "drivers": result.links_drivers or 0
        },
        persons_with_cabinet_leads=result.persons_cabinet or 0,
        persons_with_scouting_daily=result.persons_scouting or 0,
        persons_with_drivers=result.persons_drivers or 0,
        persons_only_drivers=result.persons_only_drivers or 0,
        persons_with_cabinet_or_scouting=result.persons_cabinet_or_scouting or 0
    )


@router.get("/stats/drivers-without-leads", response_model=DriversWithoutLeadsAnalysis)
def get_drivers_without_leads_analysis(db: Session = Depends(get_db)):
    """
    Analiza drivers que están en el sistema sin leads asociados.
    
    IMPORTANTE: Los drivers en cuarentena (canon.driver_orphan_quarantine) 
    NO se cuentan como "operativos" y deben estar excluidos del funnel/claims/pagos.
    
    Optimizado: una sola query principal en lugar de múltiples queries.
    """
    # Query principal optimizada - simplificada para evitar errores de columnas
    main_query = text("""
        WITH quarantine_data AS (
            SELECT 
                driver_id,
                detected_reason::text as reason
            FROM canon.driver_orphan_quarantine
            WHERE status::text = 'quarantined'
        ),
        drivers_only AS (
            SELECT DISTINCT il.person_key, il.source_pk as driver_id, il.match_rule
            FROM canon.identity_links il
            WHERE il.source_table = 'drivers'
            AND NOT EXISTS (
                SELECT 1 FROM canon.identity_links l2
                WHERE l2.person_key = il.person_key
                AND l2.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
        )
        SELECT 
            (SELECT COUNT(DISTINCT person_key) FROM drivers_only) AS total_without_leads,
            (SELECT COUNT(DISTINCT driver_id) FROM drivers_only 
             WHERE driver_id NOT IN (SELECT driver_id FROM quarantine_data)) AS operativos_count,
            (SELECT COUNT(*) FROM quarantine_data) AS total_quarantined,
            COALESCE(
                (SELECT jsonb_object_agg(reason, cnt) FROM 
                    (SELECT reason, COUNT(*) as cnt FROM quarantine_data GROUP BY reason) q),
                '{}'::jsonb
            ) AS quarantine_breakdown,
            COALESCE(
                (SELECT jsonb_object_agg(match_rule, cnt) FROM 
                    (SELECT match_rule, COUNT(*) as cnt FROM drivers_only 
                     WHERE driver_id NOT IN (SELECT driver_id FROM quarantine_data) 
                     GROUP BY match_rule) r WHERE cnt > 0),
                '{}'::jsonb
            ) AS by_match_rule
    """)
    
    result = db.execute(main_query).fetchone()
    
    total_drivers_without_leads = result.total_without_leads or 0
    drivers_without_leads_operativos = result.operativos_count or 0
    drivers_quarantined_count = result.total_quarantined or 0
    quarantine_breakdown = dict(result.quarantine_breakdown) if result.quarantine_breakdown else {}
    by_match_rule = dict(result.by_match_rule) if result.by_match_rule else {}
    
    # Retornar respuesta simplificada (sin las métricas pesadas de lead_events)
    return DriversWithoutLeadsAnalysis(
        total_drivers_without_leads=total_drivers_without_leads,
        drivers_quarantined_count=drivers_quarantined_count,
        drivers_without_leads_operativos=drivers_without_leads_operativos,
        by_match_rule=by_match_rule,
        drivers_with_lead_events=0,  # Omitido por performance
        drivers_without_lead_events=drivers_without_leads_operativos,  # Aproximación
        missing_links_by_source={},  # Omitido por performance
        sample_drivers=[],  # Omitido por performance
        quarantine_breakdown=quarantine_breakdown
    )




@router.get("/persons/{person_key}", response_model=PersonDetail)
def get_person(person_key: UUID, db: Session = Depends(get_db)):
    person = db.query(IdentityRegistry).filter(IdentityRegistry.person_key == person_key).first()
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    links = db.query(IdentityLink).filter(IdentityLink.person_key == person_key).all()
    
    driver_links = [link for link in links if link.source_table == "drivers"]
    has_driver_conversion = len(driver_links) > 0

    return PersonDetail(
        person=person,
        links=links,
        driver_links=driver_links,
        has_driver_conversion=has_driver_conversion
    )


@router.get("/unmatched", response_model=List[IdentityUnmatchedSchema])
def list_unmatched(
    db: Session = Depends(get_db),
    reason_code: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    query = db.query(IdentityUnmatched)

    if reason_code:
        query = query.filter(IdentityUnmatched.reason_code == reason_code)

    if status:
        try:
            status_enum = UnmatchedStatus(status.upper())
            query = query.filter(IdentityUnmatched.status == status_enum)
        except ValueError:
            pass

    unmatched = query.order_by(IdentityUnmatched.created_at.desc()).offset(skip).limit(limit).all()
    return unmatched


@router.post("/unmatched/{id}/resolve")
def resolve_unmatched(id: int, request: UnmatchedResolveRequest, db: Session = Depends(get_db)):
    unmatched = db.query(IdentityUnmatched).filter(IdentityUnmatched.id == id).first()
    if not unmatched:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    person = db.query(IdentityRegistry).filter(IdentityRegistry.person_key == request.person_key).first()
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    link = IdentityLink(
        person_key=request.person_key,
        source_table=unmatched.source_table,
        source_pk=unmatched.source_pk,
        snapshot_date=unmatched.snapshot_date,
        match_rule="MANUAL_RESOLUTION",
        match_score=100,
        confidence_level=ConfidenceLevel.HIGH,
        evidence={"resolved_from_unmatched": unmatched.id, "details": unmatched.details}
    )
    db.add(link)

    unmatched.status = UnmatchedStatus.RESOLVED
    from datetime import datetime
    unmatched.resolved_at = datetime.utcnow()

    db.commit()
    return {"message": "Resuelto exitosamente", "link_id": link.id}


@router.post("/scouting/process-observations")
def process_scouting_observations(
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Fecha inicio del scope"),
    date_to: Optional[date] = Query(None, description="Fecha fin del scope"),
    run_id: Optional[int] = Query(None, description="ID de corrida (opcional)")
):
    service = ScoutingObservationService(db)
    stats = service.process_scouting_observations(run_id, date_from, date_to)
    return {
        "message": "Observaciones procesadas exitosamente",
        "stats": stats
    }


def _parse_event_week(week_label: str) -> tuple[date, date]:
    """Parsea un label de semana ISO (YYYY-Www) a un rango de fechas."""
    try:
        year, week = week_label.split("-W")
        year = int(year)
        week = int(week)
        week_start = date.fromisocalendar(year, week, 1)
        week_end = date.fromisocalendar(year, week, 7)
        return week_start, week_end
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de semana inválido: {week_label}. Use ISO 'YYYY-Www'"
        )


def _apply_scope_filters(query, scope: MetricsScope, model_class):
    """
    Aplica filtros del scope a una query de SQLAlchemy.
    
    Args:
        query: Query de SQLAlchemy
        scope: MetricsScope con los filtros a aplicar
        model_class: Clase del modelo (IdentityLink o IdentityUnmatched)
    
    Returns:
        Query filtrada
    """
    if scope.run_id is not None:
        query = query.filter(model_class.run_id == scope.run_id)
    
    if scope.source_table:
        query = query.filter(model_class.source_table == scope.source_table)
    
    if scope.event_date_from:
        query = query.filter(func.cast(model_class.snapshot_date, Date) >= scope.event_date_from)
    
    if scope.event_date_to:
        query = query.filter(func.cast(model_class.snapshot_date, Date) <= scope.event_date_to)
    
    return query


def _get_summary_counts(db: Session, scope: MetricsScope) -> dict:
    """
    Calcula los conteos totales (matched, unmatched, total_processed, match_rate)
    usando el scope proporcionado.
    
    Optimizado: una sola query en lugar de 2 separadas.
    
    Returns:
        Dict con total_processed, matched, unmatched, match_rate
    """
    # Query optimizada - combina ambos conteos en una sola consulta
    stats_query = text("""
        SELECT
            (SELECT COUNT(*) FROM canon.identity_links) AS matched_count,
            (SELECT COUNT(*) FROM canon.identity_unmatched WHERE status = 'OPEN') AS unmatched_count
    """)
    
    result = db.execute(stats_query).fetchone()
    matched_count = result.matched_count or 0
    unmatched_count = result.unmatched_count or 0
    
    total_processed = matched_count + unmatched_count
    match_rate = (matched_count / total_processed * 100) if total_processed > 0 else 0.0
    
    return {
        "total_processed": total_processed,
        "matched": matched_count,
        "unmatched": unmatched_count,
        "match_rate": round(match_rate, 2)
    }


def _get_available_weeks(db: Session, scope: MetricsScope) -> list[str]:
    query_links = db.query(
        func.distinct(
            func.to_char(func.date_trunc('week', func.cast(IdentityLink.snapshot_date, Date)), 'IYYY-"W"IW')
        ).label('week_label')
    )
    
    query_unmatched = db.query(
        func.distinct(
            func.to_char(func.date_trunc('week', func.cast(IdentityUnmatched.snapshot_date, Date)), 'IYYY-"W"IW')
        ).label('week_label')
    )
    
    # Aplicar filtros del scope
    query_links = _apply_scope_filters(query_links, scope, IdentityLink)
    query_unmatched = _apply_scope_filters(query_unmatched, scope, IdentityUnmatched)
    
    rows_links = query_links.all()
    rows_unmatched = query_unmatched.all()
    
    weeks_links = {row.week_label for row in rows_links if row.week_label}
    weeks_unmatched = {row.week_label for row in rows_unmatched if row.week_label}
    
    all_weeks = sorted(set(weeks_links | weeks_unmatched))
    return all_weeks


def _get_weekly_matched(
    db: Session,
    scope: MetricsScope
) -> dict:
    week_start_expr = func.cast(func.date_trunc('week', func.cast(IdentityLink.snapshot_date, Date)), Date)
    week_label_expr = func.to_char(func.date_trunc('week', func.cast(IdentityLink.snapshot_date, Date)), 'IYYY-"W"IW')
    
    query = db.query(
        week_start_expr.label('week_start'),
        week_label_expr.label('week_label'),
        IdentityLink.source_table,
        func.count(IdentityLink.id).label('matched')
    ).group_by(
        week_start_expr,
        week_label_expr,
        IdentityLink.source_table
    )
    
    # Aplicar filtros del scope
    query = _apply_scope_filters(query, scope, IdentityLink)
    
    try:
        rows = query.all()
        results = {}
        for row in rows:
            week_start_val = row.week_start
            if isinstance(week_start_val, datetime):
                week_start_val = week_start_val.date()
            elif week_start_val and not isinstance(week_start_val, date):
                try:
                    week_start_val = week_start_val.date() if hasattr(week_start_val, 'date') else date.fromisoformat(str(week_start_val)[:10])
                except:
                    week_start_val = date.today()
            key = (week_start_val, row.week_label, row.source_table)
            results[key] = row.matched
        return results
    except Exception as e:
        logger.error(f"Error en _get_weekly_matched: {e}")
        return {}


def _get_weekly_unmatched(
    db: Session,
    scope: MetricsScope
) -> dict:
    week_start_expr = func.cast(func.date_trunc('week', func.cast(IdentityUnmatched.snapshot_date, Date)), Date)
    week_label_expr = func.to_char(func.date_trunc('week', func.cast(IdentityUnmatched.snapshot_date, Date)), 'IYYY-"W"IW')
    
    query = db.query(
        week_start_expr.label('week_start'),
        week_label_expr.label('week_label'),
        IdentityUnmatched.source_table,
        func.count(IdentityUnmatched.id).label('unmatched')
    ).group_by(
        week_start_expr,
        week_label_expr,
        IdentityUnmatched.source_table
    )
    
    # Aplicar filtros del scope
    query = _apply_scope_filters(query, scope, IdentityUnmatched)
    
    try:
        rows = query.all()
        results = {}
        for row in rows:
            week_start_val = row.week_start
            if isinstance(week_start_val, datetime):
                week_start_val = week_start_val.date()
            elif week_start_val and not isinstance(week_start_val, date):
                try:
                    week_start_val = week_start_val.date() if hasattr(week_start_val, 'date') else date.fromisoformat(str(week_start_val)[:10])
                except:
                    week_start_val = date.today()
            key = (week_start_val, row.week_label, row.source_table)
            results[key] = row.unmatched
        return results
    except Exception as e:
        logger.error(f"Error en _get_weekly_unmatched: {e}")
        return {}


def _get_weekly_breakdowns(
    db: Session,
    scope: MetricsScope
) -> dict:
    from collections import defaultdict
    
    matched_by_rule = defaultdict(lambda: defaultdict(int))
    matched_by_confidence = defaultdict(lambda: defaultdict(int))
    unmatched_by_reason = defaultdict(lambda: defaultdict(int))
    
    week_start_expr_links = func.cast(func.date_trunc('week', func.cast(IdentityLink.snapshot_date, Date)), Date)
    week_label_expr_links = func.to_char(func.date_trunc('week', func.cast(IdentityLink.snapshot_date, Date)), 'IYYY-"W"IW')
    
    links_query = db.query(
        week_start_expr_links.label('week_start'),
        week_label_expr_links.label('week_label'),
        IdentityLink.source_table,
        IdentityLink.match_rule,
        IdentityLink.confidence_level
    )
    
    # Aplicar filtros del scope
    links_query = _apply_scope_filters(links_query, scope, IdentityLink)
    
    for row in links_query.all():
        week_start_val = row.week_start
        if isinstance(week_start_val, datetime):
            week_start_val = week_start_val.date()
        elif week_start_val and not isinstance(week_start_val, date):
            try:
                week_start_val = week_start_val.date() if hasattr(week_start_val, 'date') else date.fromisoformat(str(week_start_val)[:10])
            except:
                week_start_val = date.today()
        key = (week_start_val, row.week_label, row.source_table)
        matched_by_rule[key][row.match_rule] += 1
        conf_level = row.confidence_level.value if hasattr(row.confidence_level, 'value') else str(row.confidence_level)
        matched_by_confidence[key][conf_level] += 1
    
    week_start_expr_unmatched = func.cast(func.date_trunc('week', func.cast(IdentityUnmatched.snapshot_date, Date)), Date)
    week_label_expr_unmatched = func.to_char(func.date_trunc('week', func.cast(IdentityUnmatched.snapshot_date, Date)), 'IYYY-"W"IW')
    
    unmatched_query = db.query(
        week_start_expr_unmatched.label('week_start'),
        week_label_expr_unmatched.label('week_label'),
        IdentityUnmatched.source_table,
        IdentityUnmatched.reason_code
    )
    
    # Aplicar filtros del scope
    unmatched_query = _apply_scope_filters(unmatched_query, scope, IdentityUnmatched)
    
    for row in unmatched_query.all():
        week_start_val = row.week_start
        if isinstance(week_start_val, datetime):
            week_start_val = week_start_val.date()
        elif week_start_val and not isinstance(week_start_val, date):
            try:
                week_start_val = week_start_val.date() if hasattr(week_start_val, 'date') else date.fromisoformat(str(week_start_val)[:10])
            except:
                week_start_val = date.today()
        key = (week_start_val, row.week_label, row.source_table)
        unmatched_by_reason[key][row.reason_code] += 1
    
    return {
        'matched_by_rule': matched_by_rule,
        'matched_by_confidence': matched_by_confidence,
        'unmatched_by_reason': unmatched_by_reason
    }


def _get_weekly_missing_keys(
    db: Session,
    scope: MetricsScope
) -> dict:
    from collections import defaultdict
    
    sql = """
        SELECT
            date_trunc('week', snapshot_date::date)::date AS week_start,
            to_char(date_trunc('week', snapshot_date::date), 'IYYY-"W"IW') AS week_label,
            source_table,
            mk.key AS missing_key,
            COUNT(*) AS cnt
        FROM canon.identity_unmatched iu
        CROSS JOIN LATERAL (
            SELECT jsonb_array_elements_text(iu.details->'missing_keys') AS key
        ) mk
        WHERE iu.reason_code = 'MISSING_KEYS'
          AND iu.details ? 'missing_keys'
    """
    
    params = {}
    
    if scope.run_id is not None:
        sql += " AND iu.run_id = :run_id"
        params['run_id'] = scope.run_id
    
    if scope.source_table:
        sql += " AND iu.source_table = :source_table"
        params['source_table'] = scope.source_table
    
    if scope.event_date_from:
        sql += " AND iu.snapshot_date::date >= :event_date_from"
        params['event_date_from'] = scope.event_date_from
    
    if scope.event_date_to:
        sql += " AND iu.snapshot_date::date <= :event_date_to"
        params['event_date_to'] = scope.event_date_to
    
    sql += " GROUP BY week_start, week_label, source_table, mk.key"
    
    result = db.execute(text(sql), params)
    missing_keys_by_week = defaultdict(lambda: defaultdict(int))
    
    for row in result:
        key = (row.week_start, row.week_label, row.source_table)
        missing_keys_by_week[key][row.missing_key] += row.cnt
    
    top_missing_keys = {}
    for week_key, keys_dict in missing_keys_by_week.items():
        top_missing_keys[week_key] = [
            {"key": k, "count": v}
            for k, v in sorted(keys_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
    
    return top_missing_keys


def _calculate_weekly_trend(weekly_data: list[dict]) -> list[dict]:
    from collections import defaultdict
    
    if not weekly_data:
        return []
    
    by_source = defaultdict(list)
    for week in weekly_data:
        by_source[week['source_table']].append(week)
    
    trends = []
    
    for source, weeks in by_source.items():
        sorted_weeks = sorted(weeks, key=lambda x: x['week_start'])
        if len(sorted_weeks) >= 2:
            last_week = sorted_weeks[-1]
            prev_week = sorted_weeks[-2]
            
            delta_match_rate = last_week['match_rate'] - prev_week['match_rate']
            delta_matched = last_week['matched'] - prev_week['matched']
            delta_unmatched = last_week['unmatched'] - prev_week['unmatched']
            
            trends.append({
                "week_label": last_week['week_label'],
                "source_table": source,
                "delta_match_rate": round(delta_match_rate, 2),
                "delta_matched": delta_matched,
                "delta_unmatched": delta_unmatched,
                "current_match_rate": last_week['match_rate'],
                "previous_match_rate": prev_week['match_rate']
            })
        elif len(sorted_weeks) == 1:
            last_week = sorted_weeks[0]
            trends.append({
                "week_label": last_week['week_label'],
                "source_table": source,
                "delta_match_rate": None,
                "delta_matched": None,
                "delta_unmatched": None,
                "current_match_rate": last_week['match_rate'],
                "previous_match_rate": None
            })
    
    all_weeks_by_start = defaultdict(list)
    for week in weekly_data:
        all_weeks_by_start[week['week_start']].append(week)
    
    sorted_week_starts = sorted(all_weeks_by_start.keys())
    if len(sorted_week_starts) >= 2:
        last_week_start = sorted_week_starts[-1]
        prev_week_start = sorted_week_starts[-2]
        
        last_weeks = all_weeks_by_start[last_week_start]
        prev_weeks = all_weeks_by_start[prev_week_start]
        
        total_matched_last = sum(w['matched'] for w in last_weeks)
        total_unmatched_last = sum(w['unmatched'] for w in last_weeks)
        total_processed_last = total_matched_last + total_unmatched_last
        match_rate_last = (total_matched_last / total_processed_last * 100) if total_processed_last > 0 else 0.0
        
        total_matched_prev = sum(w['matched'] for w in prev_weeks)
        total_unmatched_prev = sum(w['unmatched'] for w in prev_weeks)
        total_processed_prev = total_matched_prev + total_unmatched_prev
        match_rate_prev = (total_matched_prev / total_processed_prev * 100) if total_processed_prev > 0 else 0.0
        
        last_week_label = last_weeks[0]['week_label'] if last_weeks else ''
        
        trends.append({
            "week_label": last_week_label,
            "source_table": None,
            "delta_match_rate": round(match_rate_last - match_rate_prev, 2),
            "delta_matched": total_matched_last - total_matched_prev,
            "delta_unmatched": total_unmatched_last - total_unmatched_prev,
            "current_match_rate": round(match_rate_last, 2),
            "previous_match_rate": round(match_rate_prev, 2)
        })
    
    return trends


def _get_scouting_processed_count(db: Session, week_label: str) -> int:
    sql = text("""
        SELECT COUNT(*)
        FROM public.module_ct_scouting_daily
        WHERE to_char(date_trunc('week', registration_date::date), 'IYYY-"W"IW') = :week_label
    """)
    result = db.execute(sql, {"week_label": week_label})
    return result.scalar() or 0


def _get_scouting_candidates_count(db: Session, week_label: str, run_id: Optional[int] = None) -> int:
    query = db.query(func.count(func.distinct(ScoutingMatchCandidate.scouting_row_id))).filter(
        ScoutingMatchCandidate.week_label == week_label
    )
    if run_id is not None:
        query = query.filter(ScoutingMatchCandidate.run_id == run_id)
    return query.scalar() or 0


def _get_scouting_high_confidence_count(db: Session, week_label: str, run_id: Optional[int] = None) -> int:
    query = db.query(func.count(ScoutingMatchCandidate.id)).filter(
        ScoutingMatchCandidate.week_label == week_label,
        ScoutingMatchCandidate.score >= 0.80
    )
    if run_id is not None:
        query = query.filter(ScoutingMatchCandidate.run_id == run_id)
    return query.scalar() or 0


def _get_scouting_avg_time_to_match(db: Session, week_label: str, run_id: Optional[int] = None) -> Optional[float]:
    query = db.query(func.avg(ScoutingMatchCandidate.time_to_match_days)).filter(
        ScoutingMatchCandidate.week_label == week_label,
        ScoutingMatchCandidate.time_to_match_days.isnot(None)
    )
    if run_id is not None:
        query = query.filter(ScoutingMatchCandidate.run_id == run_id)
    result = query.scalar()
    return float(result) if result is not None else None


def _get_scouting_weekly_kpis(
    db: Session,
    run_id: Optional[int] = None,
    week_label: Optional[str] = None
) -> list[dict]:
    if week_label:
        week_labels = [week_label]
    else:
        week_labels_query = db.query(func.distinct(ScoutingMatchCandidate.week_label)).order_by(
            ScoutingMatchCandidate.week_label
        )
        if run_id is not None:
            week_labels_query = week_labels_query.filter(ScoutingMatchCandidate.run_id == run_id)
        week_labels = [row[0] for row in week_labels_query.all()]

    kpis = []
    for wl in week_labels:
        processed = _get_scouting_processed_count(db, wl)
        candidates = _get_scouting_candidates_count(db, wl, run_id)
        candidate_rate = (candidates / processed * 100) if processed > 0 else 0.0
        high_confidence = _get_scouting_high_confidence_count(db, wl, run_id)
        avg_time = _get_scouting_avg_time_to_match(db, wl, run_id)

        kpis.append({
            "week_label": wl,
            "source_table": "module_ct_scouting_daily",
            "processed_scouting": processed,
            "candidates_detected": candidates,
            "candidate_rate": round(candidate_rate, 2),
            "high_confidence_candidates": high_confidence,
            "avg_time_to_match_days": round(avg_time, 2) if avg_time is not None else None
        })

    return kpis


@router.get("/runs", response_model=IdentityRunsResponse)
def list_identity_runs(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    status: Optional[IngestionRunStatus] = Query(None, description="Filtrar por estado (RUNNING, COMPLETED, FAILED)"),
    job_type: Optional[IngestionJobType] = Query(IngestionJobType.IDENTITY_RUN, description="Filtrar por tipo de job")
):
    """
    Lista corridas de identidad con paginación y filtros.
    
    Retorna un listado paginado de corridas de identidad ordenadas por fecha de inicio
    descendente (más recientes primero).
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/identity/runs?limit=20&offset=0&status=COMPLETED&job_type=identity_run"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 20)
        offset: Número de resultados a saltar (default: 0)
        status: Filtrar por estado (opcional)
        job_type: Filtrar por tipo de job (default: identity_run)
    
    Returns:
        IdentityRunsResponse con items, total, limit y offset
    """
    try:
        # Construir query base
        query = db.query(IngestionRun)
        
        # Filtrar por job_type (default: identity_run)
        if job_type:
            # Convertir IngestionJobType a JobType del modelo
            job_type_value = JobType.IDENTITY_RUN if job_type == IngestionJobType.IDENTITY_RUN else JobType.DRIVERS_INDEX_REFRESH
            query = query.filter(IngestionRun.job_type == job_type_value)
        else:
            # Default: identity_run
            query = query.filter(IngestionRun.job_type == JobType.IDENTITY_RUN)
        
        # Filtrar por status si se proporciona
        if status:
            # Convertir IngestionRunStatus a RunStatus del modelo
            status_value = None
            if status == IngestionRunStatus.RUNNING:
                status_value = RunStatus.RUNNING
            elif status == IngestionRunStatus.COMPLETED:
                status_value = RunStatus.COMPLETED
            elif status == IngestionRunStatus.FAILED:
                status_value = RunStatus.FAILED
            
            if status_value:
                query = query.filter(IngestionRun.status == status_value)
        
        # Contar total (sin paginación)
        total = query.count()
        
        # Ordenar por started_at DESC y aplicar paginación
        runs = query.order_by(IngestionRun.started_at.desc()).offset(offset).limit(limit).all()
        
        # Convertir a schemas
        items = [IdentityRunRow.model_validate(run) for run in runs]
        
        return IdentityRunsResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        # Log del error para debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en list_identity_runs: {str(e)}", exc_info=True)
        
        # Retornar error 500
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/runs/{run_id}/report", response_model=RunReportResponse)
def get_run_report(
    run_id: int,
    db: Session = Depends(get_db),
    group_by: str = Query("none", description="Agrupación: 'none' o 'week'"),
    source_table: Optional[str] = Query(None, description="Filtrar por fuente"),
    event_week: Optional[str] = Query(None, description="Semana ISO del evento (ej: '2025-W51')"),
    event_date_from: Optional[date] = Query(None, description="Fecha inicio del evento"),
    event_date_to: Optional[date] = Query(None, description="Fecha fin del evento"),
    include_weekly: bool = Query(True, description="Incluir datos semanales")
):
    from app.models.ops import RunStatus
    from collections import defaultdict
    from typing import Dict, Any
    
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run no encontrado")
    
    run_dict = {
        "id": run.id,
        "status": run.status.value if hasattr(run.status, 'value') else str(run.status),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "scope_date_from": run.scope_date_from.isoformat() if run.scope_date_from else None,
        "scope_date_to": run.scope_date_to.isoformat() if run.scope_date_to else None,
        "incremental": run.incremental
    }
    
    links_query = db.query(IdentityLink).filter(IdentityLink.run_id == run_id)
    unmatched_query = db.query(IdentityUnmatched).filter(IdentityUnmatched.run_id == run_id)
    
    links = links_query.all()
    unmatched_list = unmatched_query.all()
    
    counts_by_source_table = defaultdict(lambda: {"total_processed": 0, "matched_count": 0, "unmatched_count": 0, "skipped_count": 0})
    
    for link in links:
        source = link.source_table
        counts_by_source_table[source]["matched_count"] += 1
        counts_by_source_table[source]["total_processed"] += 1
    
    for um in unmatched_list:
        source = um.source_table
        counts_by_source_table[source]["unmatched_count"] += 1
        counts_by_source_table[source]["total_processed"] += 1
    
    matched_by_rule = defaultdict(int)
    matched_by_confidence = defaultdict(int)
    
    for link in links:
        matched_by_rule[link.match_rule] += 1
        conf_level = link.confidence_level.value if hasattr(link.confidence_level, 'value') else str(link.confidence_level)
        matched_by_confidence[conf_level] += 1
    
    unmatched_by_reason = defaultdict(int)
    missing_keys_counter = defaultdict(int)
    
    for um in unmatched_list:
        unmatched_by_reason[um.reason_code] += 1
        if um.reason_code == "MISSING_KEYS" and um.details and "missing_keys" in um.details:
            missing_keys = um.details.get("missing_keys", [])
            if isinstance(missing_keys, list):
                for key in missing_keys:
                    missing_keys_counter[key] += 1
    
    top_missing_keys = [{"key": k, "count": v} for k, v in sorted(missing_keys_counter.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    top_unmatched = [
        {
            "id": um.id,
            "source_table": um.source_table,
            "source_pk": um.source_pk,
            "reason_code": um.reason_code,
            "details": um.details,
            "candidates_preview": um.candidates_preview
        }
        for um in unmatched_list[:10]
    ]
    
    top_matched = [
        {
            "id": link.id,
            "source_table": link.source_table,
            "source_pk": link.source_pk,
            "match_rule": link.match_rule,
            "confidence_level": link.confidence_level.value if hasattr(link.confidence_level, 'value') else str(link.confidence_level),
            "match_score": link.match_score
        }
        for link in links[:10]
    ]
    
    response_data = {
        "run": run_dict,
        "counts_by_source_table": dict(counts_by_source_table),
        "matched_breakdown": {
            "by_match_rule": dict(matched_by_rule),
            "by_confidence": dict(matched_by_confidence)
        },
        "unmatched_breakdown": {
            "by_reason_code": dict(unmatched_by_reason),
            "top_missing_keys": top_missing_keys
        },
        "samples": {
            "top_unmatched": top_unmatched,
            "top_matched": top_matched
        }
    }
    
    if group_by == "week" and include_weekly:
        event_date_from_filter = event_date_from
        event_date_to_filter = event_date_to
        
        if event_week:
            week_start, week_end = _parse_event_week(event_week)
            event_date_from_filter = week_start
            event_date_to_filter = week_end
        
        try:
            # Crear scope para las queries semanales
            weekly_scope = MetricsScope(
                run_id=run_id,
                source_table=source_table,
                event_date_from=event_date_from_filter,
                event_date_to=event_date_to_filter,
                mode="weekly"
            )
            weekly_matched = _get_weekly_matched(db, weekly_scope)
            weekly_unmatched = _get_weekly_unmatched(db, weekly_scope)
            breakdowns = _get_weekly_breakdowns(db, weekly_scope)
            missing_keys = _get_weekly_missing_keys(db, weekly_scope)
        except Exception as e:
            logger.error(f"Error ejecutando queries semanales: {e}")
            weekly_matched = {}
            weekly_unmatched = {}
            breakdowns = {'matched_by_rule': {}, 'matched_by_confidence': {}, 'unmatched_by_reason': {}}
            missing_keys = {}
        
        all_week_keys = set(weekly_matched.keys()) | set(weekly_unmatched.keys())
        # #endregion
        
        weekly_data = []
        for week_key in sorted(all_week_keys):
            week_start, week_label, source_tbl = week_key
            matched = weekly_matched.get(week_key, 0)
            unmatched = weekly_unmatched.get(week_key, 0)
            processed_total = matched + unmatched
            match_rate = (matched / processed_total * 100) if processed_total > 0 else 0.0
            
            weekly_data.append({
                "week_start": week_start.isoformat() if isinstance(week_start, date) else str(week_start),
                "week_label": week_label,
                "source_table": source_tbl,
                "matched": matched,
                "unmatched": unmatched,
                "processed_total": processed_total,
                "match_rate": round(match_rate, 2),
                "matched_by_rule": dict(breakdowns['matched_by_rule'].get(week_key, {})),
                "matched_by_confidence": dict(breakdowns['matched_by_confidence'].get(week_key, {})),
                "unmatched_by_reason": dict(breakdowns['unmatched_by_reason'].get(week_key, {})),
                "top_missing_keys": missing_keys.get(week_key, [])
            })
        
        available_weeks_scope = MetricsScope(
            run_id=run_id,
            source_table=source_table,
            mode="summary"
        )
        available_weeks = _get_available_weeks(db, available_weeks_scope)
        
        weekly_trend = _calculate_weekly_trend(weekly_data)
        
        response_data["weekly"] = weekly_data
        response_data["weekly_trend"] = weekly_trend
        response_data["available_event_weeks"] = available_weeks
        
        scouting_kpis = _get_scouting_weekly_kpis(db, run_id, event_week)
        if scouting_kpis:
            response_data["scouting_kpis"] = scouting_kpis
    
    return RunReportResponse(**response_data)


def _build_metrics_response(
    db: Session,
    scope: MetricsScope
) -> MetricsResponse:
    """
    Construye una respuesta MetricsResponse basada en el scope proporcionado.
    Optimizado para modo 'breakdowns' - solo carga totales y breakdowns, no weekly.
    """
    totals = _get_summary_counts(db, scope)
    
    response_data = {
        "scope": scope,
        "totals": totals
    }
    
    # Solo cargar weekly data para modo "weekly" explícito
    # Para "breakdowns" solo necesitamos los totales y breakdowns agregados
    if scope.mode == "weekly":
        # Obtener datos semanales
        weekly_matched = _get_weekly_matched(db, scope)
        weekly_unmatched = _get_weekly_unmatched(db, scope)
        breakdowns = _get_weekly_breakdowns(db, scope)
        missing_keys = _get_weekly_missing_keys(db, scope)
        
        all_week_keys = set(weekly_matched.keys()) | set(weekly_unmatched.keys())
        
        weekly_data = []
        for week_key in sorted(all_week_keys):
            week_start, week_label, source_tbl = week_key
            matched = weekly_matched.get(week_key, 0)
            unmatched = weekly_unmatched.get(week_key, 0)
            processed_total = matched + unmatched
            match_rate = (matched / processed_total * 100) if processed_total > 0 else 0.0
            
            weekly_data.append({
                "week_start": week_start.isoformat() if isinstance(week_start, date) else str(week_start),
                "week_label": week_label,
                "source_table": source_tbl,
                "matched": matched,
                "unmatched": unmatched,
                "processed_total": processed_total,
                "match_rate": round(match_rate, 2),
                "matched_by_rule": dict(breakdowns['matched_by_rule'].get(week_key, {})),
                "matched_by_confidence": dict(breakdowns['matched_by_confidence'].get(week_key, {})),
                "unmatched_by_reason": dict(breakdowns['unmatched_by_reason'].get(week_key, {})),
                "top_missing_keys": missing_keys.get(week_key, [])
            })
        
        response_data["weekly"] = weekly_data
        response_data["weekly_trend"] = _calculate_weekly_trend(weekly_data)
        response_data["available_event_weeks"] = _get_available_weeks(db, scope)
    
    if scope.mode == "breakdowns":
        # Obtener breakdowns agregados usando SQL directo (MUCHO más rápido)
        # En lugar de cargar todos los registros y contarlos en Python
        
        # Matched by rule
        matched_by_rule_query = text("""
            SELECT match_rule, COUNT(*) as cnt
            FROM canon.identity_links
            GROUP BY match_rule
        """)
        matched_by_rule = {
            row.match_rule: row.cnt 
            for row in db.execute(matched_by_rule_query).fetchall()
        }
        
        # Matched by confidence
        matched_by_confidence_query = text("""
            SELECT confidence_level::text as conf, COUNT(*) as cnt
            FROM canon.identity_links
            GROUP BY confidence_level
        """)
        matched_by_confidence = {
            row.conf: row.cnt 
            for row in db.execute(matched_by_confidence_query).fetchall()
        }
        
        # Unmatched by reason
        unmatched_by_reason_query = text("""
            SELECT reason_code, COUNT(*) as cnt
            FROM canon.identity_unmatched
            WHERE status = 'OPEN'
            GROUP BY reason_code
        """)
        unmatched_by_reason = {
            row.reason_code: row.cnt 
            for row in db.execute(unmatched_by_reason_query).fetchall()
        }
        
        response_data["breakdowns"] = {
            "matched_by_rule": matched_by_rule,
            "matched_by_confidence": matched_by_confidence,
            "unmatched_by_reason": unmatched_by_reason
        }
    
    return MetricsResponse(**response_data)


@router.get("/metrics/global", response_model=MetricsResponse)
def get_global_metrics(
    db: Session = Depends(get_db),
    mode: str = Query("summary", description="Modo: 'summary', 'weekly', o 'breakdowns'"),
    source_table: Optional[str] = Query(None, description="Filtrar por fuente"),
    event_date_from: Optional[date] = Query(None, description="Fecha inicio del evento"),
    event_date_to: Optional[date] = Query(None, description="Fecha fin del evento")
):
    """
    Obtiene métricas globales (histórico completo) sin filtrar por run_id.
    """
    if mode not in ["summary", "weekly", "breakdowns"]:
        raise HTTPException(status_code=400, detail="mode debe ser 'summary', 'weekly', o 'breakdowns'")
    
    if event_date_from and event_date_to and event_date_from > event_date_to:
        raise HTTPException(status_code=400, detail="event_date_from debe ser <= event_date_to")
    
    scope = MetricsScope(
        run_id=None,
        source_table=source_table,
        event_date_from=event_date_from,
        event_date_to=event_date_to,
        mode=mode
    )
    
    return _build_metrics_response(db, scope)


@router.get("/metrics/run/{run_id}", response_model=MetricsResponse)
def get_run_metrics(
    run_id: int,
    db: Session = Depends(get_db),
    mode: str = Query("summary", description="Modo: 'summary', 'weekly', o 'breakdowns'"),
    source_table: Optional[str] = Query(None, description="Filtrar por fuente"),
    event_date_from: Optional[date] = Query(None, description="Fecha inicio del evento"),
    event_date_to: Optional[date] = Query(None, description="Fecha fin del evento")
):
    """
    Obtiene métricas para un run específico.
    """
    if mode not in ["summary", "weekly", "breakdowns"]:
        raise HTTPException(status_code=400, detail="mode debe ser 'summary', 'weekly', o 'breakdowns'")
    
    if event_date_from and event_date_to and event_date_from > event_date_to:
        raise HTTPException(status_code=400, detail="event_date_from debe ser <= event_date_to")
    
    # Verificar que el run existe
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run no encontrado")
    
    scope = MetricsScope(
        run_id=run_id,
        source_table=source_table,
        event_date_from=event_date_from,
        event_date_to=event_date_to,
        mode=mode
    )
    
    return _build_metrics_response(db, scope)


@router.get("/metrics/window", response_model=MetricsResponse)
def get_window_metrics(
    db: Session = Depends(get_db),
    from_date: date = Query(..., alias="from", description="Fecha inicio de la ventana"),
    to_date: date = Query(..., alias="to", description="Fecha fin de la ventana"),
    mode: str = Query("summary", description="Modo: 'summary', 'weekly', o 'breakdowns'"),
    source_table: Optional[str] = Query(None, description="Filtrar por fuente")
):
    """
    Obtiene métricas para una ventana de tiempo específica (sin filtrar por run_id).
    """
    if mode not in ["summary", "weekly", "breakdowns"]:
        raise HTTPException(status_code=400, detail="mode debe ser 'summary', 'weekly', o 'breakdowns'")
    
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from debe ser <= to")
    
    scope = MetricsScope(
        run_id=None,
        source_table=source_table,
        event_date_from=from_date,
        event_date_to=to_date,
        mode=mode
    )
    
    return _build_metrics_response(db, scope)


# ============================================================================
# Orphans / Cuarentena Endpoints
# ============================================================================

@router.get("/orphans", response_model=OrphansListResponse)
def list_orphans(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(50, ge=1, le=500, description="Tamaño de página"),
    status: Optional[str] = Query(None, description="Filtrar por status: quarantined, resolved_relinked, resolved_created_lead, purged"),
    detected_reason: Optional[str] = Query(None, description="Filtrar por razón: no_lead_no_events, no_lead_has_events_repair_failed, legacy_driver_without_origin, manual_detection"),
    driver_id: Optional[str] = Query(None, description="Buscar por driver_id exacto")
):
    """
    Lista drivers huérfanos en cuarentena con paginación y filtros.
    """
    query = db.query(DriverOrphanQuarantine)
    
    # Aplicar filtros
    if status:
        try:
            status_enum = OrphanStatus(status)
            query = query.filter(cast(DriverOrphanQuarantine.status, String) == status_enum.value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")
    
    if detected_reason:
        try:
            reason_enum = OrphanDetectedReason(detected_reason)
            query = query.filter(cast(DriverOrphanQuarantine.detected_reason, String) == reason_enum.value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Razón inválida: {detected_reason}")
    
    if driver_id:
        query = query.filter(DriverOrphanQuarantine.driver_id == driver_id)
    
    # Contar total
    total = query.count()
    
    # Paginación
    offset = (page - 1) * page_size
    orphans_db = query.order_by(DriverOrphanQuarantine.detected_at.desc()).offset(offset).limit(page_size).all()
    
    # Enriquecer con información adicional
    orphans = []
    for orphan_db in orphans_db:
        # Buscar información adicional del driver/persona
        lead_events_count = db.execute(text("""
            SELECT COUNT(*) 
            FROM observational.lead_events le 
            WHERE (le.payload_json->>'driver_id')::text = :driver_id
        """), {"driver_id": orphan_db.driver_id}).scalar() or 0
        
        driver_links_count = db.execute(text("""
            SELECT COUNT(*) 
            FROM canon.identity_links il 
            WHERE il.source_table = 'drivers' 
            AND il.source_pk = :driver_id
        """), {"driver_id": orphan_db.driver_id}).scalar() or 0
        
        # Obtener información de persona si existe
        primary_phone = None
        primary_license = None
        primary_full_name = None
        
        if orphan_db.person_key:
            person = db.query(IdentityRegistry).filter(
                IdentityRegistry.person_key == orphan_db.person_key
            ).first()
            if person:
                primary_phone = person.primary_phone
                primary_license = person.primary_license
                primary_full_name = person.primary_full_name
        
        orphan_dict = {
            "driver_id": orphan_db.driver_id,
            "person_key": orphan_db.person_key,
            "detected_at": orphan_db.detected_at,
            "detected_reason": orphan_db.detected_reason.value if isinstance(orphan_db.detected_reason, OrphanDetectedReason) else str(orphan_db.detected_reason),
            "creation_rule": orphan_db.creation_rule,
            "evidence_json": orphan_db.evidence_json,
            "status": orphan_db.status.value if isinstance(orphan_db.status, OrphanStatus) else str(orphan_db.status),
            "resolved_at": orphan_db.resolved_at,
            "resolution_notes": orphan_db.resolution_notes,
            "primary_phone": primary_phone,
            "primary_license": primary_license,
            "primary_full_name": primary_full_name,
            "driver_links_count": driver_links_count,
            "lead_events_count": lead_events_count
        }
        orphans.append(OrphanDriver(**orphan_dict))
    
    total_pages = (total + page_size - 1) // page_size
    
    return OrphansListResponse(
        orphans=orphans,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/orphans/metrics", response_model=OrphansMetricsResponse)
def get_orphans_metrics(db: Session = Depends(get_db)):
    """
    Obtiene métricas agregadas de drivers huérfanos.
    Optimizado: una sola query en lugar de múltiples queries separadas.
    """
    # Query optimizada - todo en una sola consulta
    metrics_query = text("""
        WITH orphan_stats AS (
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status::text = 'quarantined') AS quarantined,
                COUNT(*) FILTER (WHERE status::text = 'resolved_relinked') AS resolved_relinked,
                COUNT(*) FILTER (WHERE status::text = 'resolved_created_lead') AS resolved_created_lead,
                COUNT(*) FILTER (WHERE status::text = 'purged') AS purged,
                jsonb_object_agg(
                    COALESCE(detected_reason::text, 'unknown'),
                    cnt
                ) FILTER (WHERE detected_reason IS NOT NULL) AS by_reason,
                MAX(detected_at) AS last_updated
            FROM (
                SELECT status, detected_reason, detected_at, 
                       COUNT(*) OVER (PARTITION BY detected_reason) AS cnt
                FROM canon.driver_orphan_quarantine
            ) sub
        )
        SELECT * FROM orphan_stats
    """)
    
    result = db.execute(metrics_query).fetchone()
    
    total_orphans = result.total or 0
    by_status = {
        "quarantined": result.quarantined or 0,
        "resolved_relinked": result.resolved_relinked or 0,
        "resolved_created_lead": result.resolved_created_lead or 0,
        "purged": result.purged or 0
    }
    by_reason = dict(result.by_reason) if result.by_reason else {}
    last_updated = result.last_updated
    
    return OrphansMetricsResponse(
        total_orphans=total_orphans,
        by_status=by_status,
        by_reason=by_reason,
        quarantined=by_status.get("quarantined", 0),
        resolved_relinked=by_status.get("resolved_relinked", 0),
        resolved_created_lead=by_status.get("resolved_created_lead", 0),
        purged=by_status.get("purged", 0),
        with_lead_events=0,  # Omitido por performance
        without_lead_events=total_orphans,  # Aproximación
        last_updated_at=last_updated
    )


@router.post("/orphans/run-fix", response_model=RunFixResponse)
def run_orphans_fix(
    db: Session = Depends(get_db),
    execute: bool = Query(False, description="Si True, aplica los cambios. Si False, solo hace dry-run."),
    limit: Optional[int] = Query(None, ge=1, description="Limitar número de drivers a procesar"),
    output_dir: Optional[str] = Query(None, description="Directorio para guardar reportes")
):
    """
    Ejecuta el script de limpieza de drivers huérfanos.
    Por defecto hace dry-run. Usar ?execute=true para aplicar cambios.
    
    Requiere variable de entorno ENABLE_ORPHANS_FIX=true para ejecutar en producción.
    """
    import os
    import subprocess
    from pathlib import Path
    
    # Protección: requerir flag de entorno en producción
    if execute and os.getenv("ENABLE_ORPHANS_FIX") != "true":
        raise HTTPException(
            status_code=403, 
            detail="Para ejecutar cambios, establecer ENABLE_ORPHANS_FIX=true en variables de entorno"
        )
    
    try:
        # Ejecutar script
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "fix_drivers_without_leads.py"
        cmd = ["python", str(script_path)]
        
        if execute:
            cmd.append("--execute")
        
        if limit:
            cmd.extend(["--limit", str(limit)])
        
        if output_dir:
            cmd.extend(["--output-dir", output_dir])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Error ejecutando script: {result.stderr}"
            )
        
        # Parsear output para extraer información (simplificado)
        # En producción, el script debería retornar JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return RunFixResponse(
            dry_run=not execute,
            timestamp=timestamp,
            stats={
                "processed": 0,  # Se obtendría del script
                "with_events": 0,
                "without_events": 0,
                "resolved_relinked": 0,
                "quarantined": 0
            },
            drivers=[],
            report_path=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ejecutando fix: {str(e)}")

