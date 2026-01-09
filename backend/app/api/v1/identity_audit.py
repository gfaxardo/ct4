"""
Endpoints de auditoría de origen canónico.

Este módulo NO afecta claims (C3) ni pagos (C4).
Solo opera sobre C0 (Identidad) y C1 (Funnel).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.db import get_db
from app.models.canon import (
    IdentityOrigin, IdentityOriginHistory, IdentityOriginAlertState,
    OriginTag, OriginResolutionStatus, AlertType
)
from app.schemas.identity_audit import (
    OriginAuditRow, OriginAlertRow, OriginAuditListResponse,
    OriginAlertListResponse, ResolveOriginRequest, MarkLegacyRequest,
    ResolveAlertRequest, MuteAlertRequest, BatchResolveRequest,
    OriginAuditStats
)
from app.services.origin_determination import OriginDeterminationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/audit/origin", response_model=OriginAuditListResponse)
def list_origin_audit(
    db: Session = Depends(get_db),
    violation_flag: Optional[bool] = Query(None, description="Filtrar por violation_flag"),
    violation_reason: Optional[str] = Query(None, description="Filtrar por violation_reason"),
    resolution_status: Optional[str] = Query(None, description="Filtrar por resolution_status"),
    origin_tag: Optional[str] = Query(None, description="Filtrar por origin_tag"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Lista auditoría de origen con filtros.
    """
    conditions = []
    params = {}
    
    if violation_flag is not None:
        conditions.append("violation_flag = :violation_flag")
        params["violation_flag"] = violation_flag
    
    if violation_reason:
        conditions.append("violation_reason = :violation_reason")
        params["violation_reason"] = violation_reason
    
    if resolution_status:
        conditions.append("resolution_status = :resolution_status")
        params["resolution_status"] = resolution_status
    
    if origin_tag:
        conditions.append("origin_tag = :origin_tag")
        params["origin_tag"] = origin_tag
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Contar total
    count_query = text(f"""
        SELECT COUNT(*) as total
        FROM ops.v_identity_origin_audit
        {where_clause}
    """)
    total_result = db.execute(count_query, params).fetchone()
    total = total_result.total if total_result else 0
    
    # Query principal con paginación
    query = text(f"""
        SELECT 
            person_key, driver_id, origin_tag, origin_source_id, origin_confidence,
            origin_created_at, ruleset_version, origin_evidence, decided_by, decided_at,
            resolution_status, notes, first_seen_at, driver_linked_at, has_lead_links,
            links_summary, violation_flag, violation_reason, recommended_action
        FROM ops.v_identity_origin_audit
        {where_clause}
        ORDER BY first_seen_at DESC
        LIMIT :limit OFFSET :skip
    """)
    params["limit"] = limit
    params["skip"] = skip
    
    rows = db.execute(query, params).fetchall()
    
    items = []
    for row in rows:
        items.append(OriginAuditRow(
            person_key=row.person_key,
            driver_id=row.driver_id,
            origin_tag=row.origin_tag,
            origin_source_id=row.origin_source_id,
            origin_confidence=float(row.origin_confidence) if row.origin_confidence else None,
            origin_created_at=row.origin_created_at,
            ruleset_version=row.ruleset_version,
            origin_evidence=row.origin_evidence,
            decided_by=row.decided_by,
            decided_at=row.decided_at,
            resolution_status=row.resolution_status,
            notes=row.notes,
            first_seen_at=row.first_seen_at,
            driver_linked_at=row.driver_linked_at,
            has_lead_links=row.has_lead_links,
            links_summary=row.links_summary,
            violation_flag=row.violation_flag,
            violation_reason=row.violation_reason,
            recommended_action=row.recommended_action
        ))
    
    return OriginAuditListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/audit/origin/{person_key}", response_model=OriginAuditRow)
def get_origin_audit_detail(person_key: UUID, db: Session = Depends(get_db)):
    """
    Obtiene detalle de auditoría de una persona específica.
    """
    query = text("""
        SELECT 
            person_key, driver_id, origin_tag, origin_source_id, origin_confidence,
            origin_created_at, ruleset_version, origin_evidence, decided_by, decided_at,
            resolution_status, notes, first_seen_at, driver_linked_at, has_lead_links,
            links_summary, violation_flag, violation_reason, recommended_action
        FROM ops.v_identity_origin_audit
        WHERE person_key = :person_key
    """)
    
    row = db.execute(query, {"person_key": str(person_key)}).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Persona no encontrada en auditoría")
    
    return OriginAuditRow(
        person_key=row.person_key,
        driver_id=row.driver_id,
        origin_tag=row.origin_tag,
        origin_source_id=row.origin_source_id,
        origin_confidence=float(row.origin_confidence) if row.origin_confidence else None,
        origin_created_at=row.origin_created_at,
        ruleset_version=row.ruleset_version,
        origin_evidence=row.origin_evidence,
        decided_by=row.decided_by,
        decided_at=row.decided_at,
        resolution_status=row.resolution_status,
        notes=row.notes,
        first_seen_at=row.first_seen_at,
        driver_linked_at=row.driver_linked_at,
        has_lead_links=row.has_lead_links,
        links_summary=row.links_summary,
        violation_flag=row.violation_flag,
        violation_reason=row.violation_reason,
        recommended_action=row.recommended_action
    )


@router.post("/audit/origin/{person_key}/resolve")
def resolve_origin_violation(
    person_key: UUID,
    request: ResolveOriginRequest,
    db: Session = Depends(get_db)
):
    """
    Resuelve una violación de origen.
    Puede crear o actualizar el registro en canon.identity_origin.
    """
    from app.services.origin_determination import OriginDeterminationService
    
    # Obtener o crear registro de origen
    origin = db.query(IdentityOrigin).filter(
        IdentityOrigin.person_key == person_key
    ).first()
    
    # Registrar cambio en historial si existe registro previo
    if origin:
        history = IdentityOriginHistory(
            person_key=person_key,
            origin_tag_old=origin.origin_tag.value if origin.origin_tag else None,
            origin_tag_new=request.origin_tag.value if request.origin_tag else origin.origin_tag.value if origin.origin_tag else None,
            origin_source_id_old=origin.origin_source_id,
            origin_source_id_new=request.origin_source_id or origin.origin_source_id,
            origin_confidence_old=float(origin.origin_confidence),
            origin_confidence_new=float(request.origin_confidence) if request.origin_confidence else float(origin.origin_confidence),
            resolution_status_old=origin.resolution_status.value,
            resolution_status_new=request.resolution_status.value,
            ruleset_version_old=origin.ruleset_version,
            ruleset_version_new=origin.ruleset_version,
            changed_by="manual",
            change_reason=request.notes or "Resolución manual de violación"
        )
        db.add(history)
        
        # Actualizar registro existente
        if request.origin_tag:
            origin.origin_tag = request.origin_tag
        if request.origin_source_id:
            origin.origin_source_id = request.origin_source_id
        if request.origin_confidence is not None:
            origin.origin_confidence = request.origin_confidence
        origin.resolution_status = request.resolution_status
        if request.notes:
            origin.notes = request.notes
        origin.updated_at = datetime.utcnow()
    else:
        # Crear nuevo registro
        if not request.origin_tag or not request.origin_source_id:
            raise HTTPException(
                status_code=400,
                detail="origin_tag y origin_source_id son requeridos para crear nuevo registro"
            )
        
        origin = IdentityOrigin(
            person_key=person_key,
            origin_tag=request.origin_tag,
            origin_source_id=request.origin_source_id,
            origin_confidence=request.origin_confidence or 100.0,
            origin_created_at=datetime.utcnow(),  # TODO: obtener desde links
            resolution_status=request.resolution_status,
            decided_by="manual",
            notes=request.notes
        )
        db.add(origin)
    
    db.commit()
    db.refresh(origin)
    
    return {"message": "Violación resuelta", "person_key": str(person_key)}


@router.post("/audit/origin/{person_key}/mark-legacy")
def mark_as_legacy(
    person_key: UUID,
    request: MarkLegacyRequest,
    db: Session = Depends(get_db)
):
    """
    Marca una persona como legacy_external.
    """
    origin = db.query(IdentityOrigin).filter(
        IdentityOrigin.person_key == person_key
    ).first()
    
    if origin:
        # Registrar cambio en historial
        history = IdentityOriginHistory(
            person_key=person_key,
            origin_tag_old=origin.origin_tag.value if origin.origin_tag else None,
            origin_tag_new=OriginTag.LEGACY_EXTERNAL.value,
            origin_source_id_old=origin.origin_source_id,
            origin_source_id_new=origin.origin_source_id,
            resolution_status_old=origin.resolution_status.value,
            resolution_status_new=OriginResolutionStatus.MARKED_LEGACY.value,
            ruleset_version_old=origin.ruleset_version,
            ruleset_version_new=origin.ruleset_version,
            changed_by="manual",
            change_reason=request.notes or "Marcado como legacy_external"
        )
        db.add(history)
        
        origin.origin_tag = OriginTag.LEGACY_EXTERNAL
        origin.resolution_status = OriginResolutionStatus.MARKED_LEGACY
        if request.notes:
            origin.notes = request.notes
        origin.updated_at = datetime.utcnow()
    else:
        # Crear nuevo registro como legacy
        origin = IdentityOrigin(
            person_key=person_key,
            origin_tag=OriginTag.LEGACY_EXTERNAL,
            origin_source_id=str(person_key),  # Usar person_key como source_id para legacy
            origin_confidence=50.0,
            origin_created_at=datetime.utcnow(),
            resolution_status=OriginResolutionStatus.MARKED_LEGACY,
            decided_by="manual",
            notes=request.notes
        )
        db.add(origin)
    
    db.commit()
    
    return {"message": "Persona marcada como legacy_external", "person_key": str(person_key)}


@router.get("/audit/alerts", response_model=OriginAlertListResponse)
def list_origin_alerts(
    db: Session = Depends(get_db),
    alert_type: Optional[str] = Query(None, description="Filtrar por alert_type"),
    severity: Optional[str] = Query(None, description="Filtrar por severity"),
    impact: Optional[str] = Query(None, description="Filtrar por impact"),
    resolved_only: Optional[bool] = Query(False, description="Solo alertas resueltas"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Lista alertas de origen con filtros.
    """
    conditions = []
    params = {}
    
    if alert_type:
        conditions.append("alert_type = :alert_type")
        params["alert_type"] = alert_type
    
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity
    
    if impact:
        conditions.append("impact = :impact")
        params["impact"] = impact
    
    if resolved_only:
        conditions.append("is_resolved_or_muted = true")
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Contar total
    count_query = text(f"""
        SELECT COUNT(*) as total
        FROM ops.v_identity_origin_alerts
        {where_clause}
    """)
    total_result = db.execute(count_query, params).fetchone()
    total = total_result.total if total_result else 0
    
    # Query principal con paginación
    query = text(f"""
        SELECT 
            alert_id, person_key, driver_id, alert_type, violation_reason,
            recommended_action, severity, impact, origin_tag, origin_confidence,
            first_seen_at, first_detected_at, last_detected_at, resolved_at,
            resolved_by, muted_until, alert_notes, is_resolved_or_muted, resolution_status
        FROM ops.v_identity_origin_alerts
        {where_clause}
        ORDER BY first_detected_at DESC
        LIMIT :limit OFFSET :skip
    """)
    params["limit"] = limit
    params["skip"] = skip
    
    rows = db.execute(query, params).fetchall()
    
    items = []
    for row in rows:
        items.append(OriginAlertRow(
            alert_id=row.alert_id,
            person_key=row.person_key,
            driver_id=row.driver_id,
            alert_type=row.alert_type,
            violation_reason=row.violation_reason,
            recommended_action=row.recommended_action,
            severity=row.severity,
            impact=row.impact,
            origin_tag=row.origin_tag,
            origin_confidence=float(row.origin_confidence) if row.origin_confidence else None,
            first_seen_at=row.first_seen_at,
            first_detected_at=row.first_detected_at,
            last_detected_at=row.last_detected_at,
            resolved_at=row.resolved_at,
            resolved_by=row.resolved_by,
            muted_until=row.muted_until,
            alert_notes=row.alert_notes,
            is_resolved_or_muted=row.is_resolved_or_muted,
            resolution_status=row.resolution_status
        ))
    
    return OriginAlertListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/audit/alerts/{person_key}/{alert_type}/resolve")
def resolve_alert(
    person_key: UUID,
    alert_type: str,
    request: ResolveAlertRequest,
    db: Session = Depends(get_db)
):
    """
    Resuelve una alerta específica.
    """
    alert_state = db.query(IdentityOriginAlertState).filter(
        IdentityOriginAlertState.person_key == person_key,
        IdentityOriginAlertState.alert_type == AlertType(alert_type)
    ).first()
    
    if not alert_state:
        # Crear nuevo estado
        alert_state = IdentityOriginAlertState(
            person_key=person_key,
            alert_type=AlertType(alert_type),
            first_detected_at=datetime.utcnow(),
            last_detected_at=datetime.utcnow(),
            resolved_at=datetime.utcnow(),
            resolved_by=request.resolved_by,
            notes=request.notes
        )
        db.add(alert_state)
    else:
        alert_state.resolved_at = datetime.utcnow()
        alert_state.resolved_by = request.resolved_by
        if request.notes:
            alert_state.notes = request.notes
        alert_state.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Alerta resuelta", "person_key": str(person_key), "alert_type": alert_type}


@router.post("/audit/alerts/{person_key}/{alert_type}/mute")
def mute_alert(
    person_key: UUID,
    alert_type: str,
    request: MuteAlertRequest,
    db: Session = Depends(get_db)
):
    """
    Silencia una alerta temporalmente.
    """
    alert_state = db.query(IdentityOriginAlertState).filter(
        IdentityOriginAlertState.person_key == person_key,
        IdentityOriginAlertState.alert_type == AlertType(alert_type)
    ).first()
    
    if not alert_state:
        alert_state = IdentityOriginAlertState(
            person_key=person_key,
            alert_type=AlertType(alert_type),
            first_detected_at=datetime.utcnow(),
            last_detected_at=datetime.utcnow(),
            muted_until=request.muted_until,
            notes=request.notes
        )
        db.add(alert_state)
    else:
        alert_state.muted_until = request.muted_until
        if request.notes:
            alert_state.notes = request.notes
        alert_state.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Alerta silenciada", "person_key": str(person_key), "alert_type": alert_type}


@router.get("/audit/stats", response_model=OriginAuditStats)
def get_audit_stats(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas de auditoría.
    """
    # Total de personas
    total_persons_query = text("SELECT COUNT(DISTINCT person_key) as total FROM ops.v_identity_origin_audit")
    total_persons = db.execute(total_persons_query).scalar() or 0
    
    # Personas con violaciones
    violations_query = text("SELECT COUNT(DISTINCT person_key) as total FROM ops.v_identity_origin_audit WHERE violation_flag = true")
    persons_with_violations = db.execute(violations_query).scalar() or 0
    
    # Violaciones por razón
    violations_by_reason_query = text("""
        SELECT violation_reason, COUNT(*) as count
        FROM ops.v_identity_origin_audit
        WHERE violation_flag = true
        GROUP BY violation_reason
    """)
    violations_by_reason = {
        row.violation_reason: row.count
        for row in db.execute(violations_by_reason_query).fetchall()
        if row.violation_reason
    }
    
    # Distribución por resolution_status
    status_query = text("""
        SELECT resolution_status, COUNT(*) as count
        FROM ops.v_identity_origin_audit
        GROUP BY resolution_status
    """)
    resolution_status_distribution = {
        row.resolution_status: row.count
        for row in db.execute(status_query).fetchall()
        if row.resolution_status
    }
    
    # Alertas por tipo
    alerts_by_type_query = text("""
        SELECT alert_type, COUNT(*) as count
        FROM ops.v_identity_origin_alerts
        WHERE is_resolved_or_muted = false
        GROUP BY alert_type
    """)
    alerts_by_type = {
        row.alert_type: row.count
        for row in db.execute(alerts_by_type_query).fetchall()
    }
    
    # Alertas por severidad
    alerts_by_severity_query = text("""
        SELECT severity, COUNT(*) as count
        FROM ops.v_identity_origin_alerts
        WHERE is_resolved_or_muted = false
        GROUP BY severity
    """)
    alerts_by_severity = {
        row.severity: row.count
        for row in db.execute(alerts_by_severity_query).fetchall()
    }
    
    # Violaciones por severidad (inferir desde alertas)
    violations_by_severity = {
        "high": sum(v for k, v in violations_by_reason.items() if k in ["missing_origin", "multiple_origins"]),
        "medium": sum(v for k, v in violations_by_reason.items() if k in ["late_origin_link", "orphan_lead"]),
        "low": sum(v for k, v in violations_by_reason.items() if k == "legacy_driver_unclassified")
    }
    
    return OriginAuditStats(
        total_persons=total_persons,
        persons_with_violations=persons_with_violations,
        violations_by_reason=violations_by_reason,
        violations_by_severity=violations_by_severity,
        resolution_status_distribution=resolution_status_distribution,
        alerts_by_type=alerts_by_type,
        alerts_by_severity=alerts_by_severity
    )

