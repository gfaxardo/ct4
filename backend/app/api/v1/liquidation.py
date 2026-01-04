from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date
from decimal import Decimal
from app.db import get_db
from app.schemas.liquidation import (
    ScoutMarkPaidRequest,
    ScoutMarkPaidResponse,
    ScoutPreviewResponse
)
from app.config import settings

router = APIRouter()


def verify_admin_token(admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Verifica el token de administrador"""
    if not settings.admin_token:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN no configurado en el servidor"
        )
    if not admin_token or admin_token != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="Token de administrador inválido o faltante"
        )
    return admin_token


@router.get("/scout/preview", response_model=ScoutPreviewResponse)
def get_scout_preview(
    db: Session = Depends(get_db),
    scout_id: int = Query(..., description="ID del scout"),
    cutoff_date: date = Query(..., description="Fecha de corte (YYYY-MM-DD)")
):
    """
    Previsualiza items que serán marcados como pagados para un scout.
    """
    query = text("""
        SELECT
            COUNT(*) AS preview_items,
            COALESCE(SUM(amount), 0) AS preview_amount
        FROM ops.v_scout_liquidation_open_items_payable_policy
        WHERE acquisition_scout_id = :scout_id
          AND payable_date <= :cutoff_date
    """)
    
    result = db.execute(query, {"scout_id": scout_id, "cutoff_date": cutoff_date}).fetchone()
    
    return ScoutPreviewResponse(
        preview_items=result.preview_items or 0,
        preview_amount=Decimal(str(result.preview_amount or 0))
    )


@router.post("/scout/mark_paid", response_model=ScoutMarkPaidResponse)
def mark_scout_paid(
    request: ScoutMarkPaidRequest,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Marca items como pagados para un scout hasta una fecha de corte.
    Requiere token de administrador en header X-Admin-Token.
    """
    # Primero obtener preview
    preview_query = text("""
        SELECT
            COUNT(*) AS preview_items,
            COALESCE(SUM(amount), 0) AS preview_amount
        FROM ops.v_scout_liquidation_open_items_payable_policy
        WHERE acquisition_scout_id = :scout_id
          AND payable_date <= :cutoff_date
    """)
    
    preview_result = db.execute(
        preview_query,
        {"scout_id": request.scout_id, "cutoff_date": request.cutoff_date}
    ).fetchone()
    
    preview_items = preview_result.preview_items or 0
    preview_amount = Decimal(str(preview_result.preview_amount or 0))
    
    if preview_items == 0:
        return ScoutMarkPaidResponse(
            inserted_items=0,
            inserted_amount=Decimal("0"),
            preview_items=0,
            preview_amount=Decimal("0"),
            message="No hay items para marcar como pagados"
        )
    
    # Ejecutar INSERT
    insert_query = text("""
        INSERT INTO ops.scout_liquidation_ledger (
            payment_item_key,
            scout_id,
            person_key,
            driver_id,
            lead_origin,
            milestone_type,
            milestone_value,
            rule_id,
            payable_date,
            achieved_date,
            amount,
            currency,
            paid_by,
            payment_ref,
            notes
        )
        SELECT
            payment_item_key,
            acquisition_scout_id,
            person_key,
            driver_id,
            lead_origin,
            milestone_type,
            milestone_value,
            rule_id,
            payable_date,
            achieved_date,
            amount,
            currency,
            :paid_by,
            :payment_ref,
            :notes
        FROM ops.v_scout_liquidation_open_items_payable_policy
        WHERE acquisition_scout_id = :scout_id
          AND payable_date <= :cutoff_date
        ON CONFLICT (payment_item_key) DO NOTHING
    """)
    
    db.execute(
        insert_query,
        {
            "scout_id": request.scout_id,
            "cutoff_date": request.cutoff_date,
            "paid_by": request.paid_by,
            "payment_ref": request.payment_ref,
            "notes": request.notes
        }
    )
    db.commit()
    
    # Medir después del INSERT para obtener inserted_items e inserted_amount
    post_preview_query = text("""
        SELECT
            COUNT(*) AS post_preview_items,
            COALESCE(SUM(amount), 0) AS post_preview_amount
        FROM ops.v_scout_liquidation_open_items_payable_policy
        WHERE acquisition_scout_id = :scout_id
          AND payable_date <= :cutoff_date
    """)
    
    post_preview_result = db.execute(
        post_preview_query,
        {"scout_id": request.scout_id, "cutoff_date": request.cutoff_date}
    ).fetchone()
    
    post_preview_items = post_preview_result.post_preview_items or 0
    post_preview_amount = Decimal(str(post_preview_result.post_preview_amount or 0))
    
    inserted_items = preview_items - post_preview_items
    inserted_amount = preview_amount - post_preview_amount
    
    return ScoutMarkPaidResponse(
        inserted_items=inserted_items,
        inserted_amount=inserted_amount,
        preview_items=preview_items,
        preview_amount=preview_amount,
        message=f"Se marcaron {inserted_items} items como pagados por un total de {inserted_amount:,.2f} PEN"
    )




















