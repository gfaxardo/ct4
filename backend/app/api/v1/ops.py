from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.models.ops import IngestionRun, Alert
from app.schemas.ingestion import IngestionRun as IngestionRunSchema
from app.services.alerts import AlertService

router = APIRouter()


@router.get("/ingestion-runs", response_model=List[IngestionRunSchema])
def list_ingestion_runs(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    runs = db.query(IngestionRun).order_by(IngestionRun.started_at.desc()).offset(skip).limit(limit).all()
    # #region agent log
    if runs and skip == 0:
        import json
        from app.models.canon import IdentityLink
        from sqlalchemy import func
        try:
            first_run = runs[0]
            links_count = db.query(func.count(IdentityLink.id)).filter(IdentityLink.run_id == first_run.id).scalar()
            with open('c:\\cursor\\CT4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "initial",
                    "hypothesisId": "B",
                    "location": "ops.py:list_ingestion_runs:first_run",
                    "message": "Última corrida (primera en lista)",
                    "data": {
                        "run_id": first_run.id,
                        "status": first_run.status.value if hasattr(first_run.status, 'value') else str(first_run.status),
                        "started_at": first_run.started_at.isoformat() if first_run.started_at else None,
                        "links_count": links_count
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }) + '\n')
        except: pass
    # #endregion
    return runs


@router.get("/alerts")
def list_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000)
):
    service = AlertService(db)
    alerts = service.get_active_alerts(limit)
    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),
            "week_label": alert.week_label,
            "message": alert.message,
            "details": alert.details,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "run_id": alert.run_id
        }
        for alert in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    alert = service.acknowledge_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"message": "Alerta reconocida exitosamente", "alert_id": alert.id}

