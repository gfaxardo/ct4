"""
Dashboard API endpoints.

Provides summary views and metrics for scouts and Yango payments.
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.db import get_db
from app.schemas.dashboard import (
    ScoutByWeek,
    ScoutOpenItem,
    ScoutOpenItemsResponse,
    ScoutSummaryResponse,
    ScoutTotals,
    TopScout,
    YangoByWeek,
    YangoReceivableItem,
    YangoReceivableItemsResponse,
    YangoSummaryResponse,
    YangoTotals,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _view_exists(db: Session, schema: str, view_name: str) -> bool:
    """Verifica si una vista existe en la base de datos."""
    try:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = :schema AND table_name = :view_name
            )
        """), {"schema": schema, "view_name": view_name})
        return result.scalar()
    except Exception:
        return False


@router.get("/scout/summary", response_model=ScoutSummaryResponse)
def get_scout_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Fecha inicio de semana"),
    week_end: Optional[date] = Query(None, description="Fecha fin de semana"),
    scout_id: Optional[int] = Query(None, description="ID del scout"),
    lead_origin: Optional[str] = Query(None, description="Origen del lead: cabinet o migration")
):
    """
    Obtiene resumen de liquidación scouts con totales, por semana y top scouts.
    
    Usa scout_liquidation_ledger como fuente primaria de datos.
    """
    # Verificar qué tabla/vista usar
    # Primero intentar con la tabla base que siempre existe
    base_table = "ops.scout_liquidation_ledger"
    
    # Construir condiciones WHERE
    where_conditions = ["paid_at IS NULL"]  # Solo items pendientes
    params = {}
    
    if week_start:
        where_conditions.append("payable_date >= :week_start")
        params["week_start"] = week_start
    if week_end:
        where_conditions.append("payable_date <= :week_end")
        params["week_end"] = week_end
    if scout_id:
        where_conditions.append("scout_id = :scout_id")
        params["scout_id"] = scout_id
    if lead_origin:
        where_conditions.append("lead_origin = :lead_origin")
        params["lead_origin"] = lead_origin
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    try:
        # Totales payable
        totals_payable_query = text(f"""
            SELECT 
                COALESCE(SUM(amount), 0) AS payable_amount,
                COUNT(*) AS payable_items,
                COUNT(DISTINCT driver_id) AS payable_drivers,
                COUNT(DISTINCT scout_id) AS payable_scouts
            FROM {base_table}
            WHERE {where_clause}
        """)
        
        result_payable = db.execute(totals_payable_query, params).fetchone()
        totals_payable = {
            "payable_amount": Decimal(str(result_payable.payable_amount or 0)),
            "payable_items": result_payable.payable_items or 0,
            "payable_drivers": result_payable.payable_drivers or 0,
            "payable_scouts": result_payable.payable_scouts or 0
        }
        
        # No hay blocked items en la tabla base
        totals_blocked = {
            "blocked_amount": Decimal("0"),
            "blocked_items": 0
        }
        
        totals = ScoutTotals(**totals_payable, **totals_blocked)
        
        # Por semana (payable)
        by_week_query = text(f"""
            SELECT 
                date_trunc('week', payable_date)::date AS week_start_monday,
                to_char(payable_date, 'IYYY-IW') AS iso_year_week,
                COALESCE(SUM(amount), 0) AS payable_amount,
                COUNT(*) AS payable_items
            FROM {base_table}
            WHERE {where_clause}
            GROUP BY week_start_monday, iso_year_week
            ORDER BY week_start_monday DESC
            LIMIT 52
        """)
        
        weeks_payable = db.execute(by_week_query, params).fetchall()
        
        by_week = [
            ScoutByWeek(
                week_start_monday=row.week_start_monday,
                iso_year_week=row.iso_year_week,
                payable_amount=Decimal(str(row.payable_amount or 0)),
                payable_items=row.payable_items or 0,
                blocked_amount=Decimal("0"),
                blocked_items=0
            )
            for row in weeks_payable
        ]
        
        # Top scouts - JOIN con v_dim_scouts para obtener nombres
        top_scouts_query = text(f"""
            SELECT 
                l.scout_id,
                COALESCE(s.scout_name_normalized, 'Scout ' || l.scout_id::text) AS scout_name,
                COALESCE(SUM(l.amount), 0) AS amount,
                COUNT(*) AS items,
                COUNT(DISTINCT l.driver_id) AS drivers
            FROM {base_table} l
            LEFT JOIN ops.v_dim_scouts s ON l.scout_id = s.scout_id
            WHERE {where_clause.replace("scout_id", "l.scout_id").replace("driver_id", "l.driver_id").replace("paid_at", "l.paid_at")}
            AND l.scout_id IS NOT NULL
            GROUP BY l.scout_id, s.scout_name_normalized
            ORDER BY amount DESC
            LIMIT 10
        """)
        
        top_scouts_rows = db.execute(top_scouts_query, params).fetchall()
        top_scouts = [
            TopScout(
                acquisition_scout_id=row.scout_id,
                acquisition_scout_name=row.scout_name,
                amount=Decimal(str(row.amount or 0)),
                items=row.items or 0,
                drivers=row.drivers or 0
            )
            for row in top_scouts_rows
        ]
        
        return ScoutSummaryResponse(
            totals=totals,
            by_week=by_week,
            top_scouts=top_scouts
        )
        
    except ProgrammingError as e:
        logger.error(f"Error en get_scout_summary: {e}")
        # Retornar respuesta vacía si hay error de tabla/vista faltante
        return ScoutSummaryResponse(
            totals=ScoutTotals(
                payable_amount=Decimal("0"),
                payable_items=0,
                payable_drivers=0,
                payable_scouts=0,
                blocked_amount=Decimal("0"),
                blocked_items=0
            ),
            by_week=[],
            top_scouts=[]
        )


@router.get("/scout/open_items", response_model=ScoutOpenItemsResponse)
def get_scout_open_items(
    db: Session = Depends(get_db),
    week_start_monday: Optional[date] = Query(None, description="Fecha inicio de semana"),
    scout_id: Optional[int] = Query(None, description="ID del scout"),
    confidence: Optional[str] = Query("policy", description="Confidence: policy, high, medium, unknown"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Obtiene items abiertos de liquidación scouts con paginación.
    """
    # Determinar vista según confidence
    if confidence == "policy":
        view_name = "ops.v_scout_liquidation_open_items_payable_policy"
        confidence_filter = ""
    elif confidence in ["high", "medium", "unknown"]:
        view_name = "ops.v_scout_liquidation_open_items_enriched"
        confidence_filter = f"AND attribution_confidence = :confidence"
    else:
        raise HTTPException(status_code=400, detail="confidence debe ser: policy, high, medium, unknown")
    
    # Construir condiciones WHERE
    where_conditions = ["1=1"]
    params = {"limit": limit, "offset": offset}
    
    if week_start_monday:
        where_conditions.append("date_trunc('week', payable_date)::date = :week_start_monday")
        params["week_start_monday"] = week_start_monday
    if scout_id:
        where_conditions.append("acquisition_scout_id = :scout_id")
        params["scout_id"] = scout_id
    if confidence_filter:
        where_conditions.append(confidence_filter.replace("AND ", ""))
        params["confidence"] = confidence
    
    where_clause = " AND ".join(where_conditions)
    
    # Contar total
    count_query = text(f"""
        SELECT COUNT(*) AS total
        FROM {view_name}
        WHERE {where_clause}
    """)
    
    total = db.execute(count_query, params).scalar()
    
    # Obtener items
    items_query = text(f"""
        SELECT 
            payment_item_key,
            person_key::text,
            lead_origin,
            scout_id,
            acquisition_scout_id,
            acquisition_scout_name,
            attribution_confidence,
            attribution_rule,
            milestone_type,
            milestone_value,
            payable_date,
            achieved_date,
            amount,
            currency,
            driver_id
        FROM {view_name}
        WHERE {where_clause}
        ORDER BY payable_date DESC, amount DESC
        LIMIT :limit OFFSET :offset
    """)
    
    rows = db.execute(items_query, params).fetchall()
    items = [
        ScoutOpenItem(
            payment_item_key=row.payment_item_key,
            person_key=row.person_key,
            lead_origin=row.lead_origin,
            scout_id=row.scout_id,
            acquisition_scout_id=row.acquisition_scout_id,
            acquisition_scout_name=row.acquisition_scout_name,
            attribution_confidence=row.attribution_confidence,
            attribution_rule=row.attribution_rule,
            milestone_type=row.milestone_type,
            milestone_value=row.milestone_value,
            payable_date=row.payable_date,
            achieved_date=row.achieved_date,
            amount=Decimal(str(row.amount or 0)),
            currency=row.currency,
            driver_id=row.driver_id
        )
        for row in rows
    ]
    
    return ScoutOpenItemsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/yango/summary", response_model=YangoSummaryResponse)
def get_yango_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Fecha inicio de semana"),
    week_end: Optional[date] = Query(None, description="Fecha fin de semana")
):
    """
    Obtiene resumen de cobranza Yango con totales y por semana.
    """
    # Construir condiciones WHERE
    where_conditions = []
    params = {}
    
    if week_start:
        where_conditions.append("pay_week_start_monday >= :week_start")
        params["week_start"] = week_start
    if week_end:
        where_conditions.append("pay_week_start_monday <= :week_end")
        params["week_end"] = week_end
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Totales
    totals_query = text(f"""
        SELECT 
            COALESCE(SUM(total_amount_payable), 0) AS receivable_amount,
            SUM(count_payments) AS receivable_items,
            SUM(count_drivers) AS receivable_drivers
        FROM ops.v_yango_receivable_payable
        WHERE {where_clause}
    """)
    
    result_totals = db.execute(totals_query, params).fetchone()
    totals = YangoTotals(
        receivable_amount=Decimal(str(result_totals.receivable_amount or 0)),
        receivable_items=result_totals.receivable_items or 0,
        receivable_drivers=result_totals.receivable_drivers or 0
    )
    
    # Por semana
    by_week_query = text(f"""
        SELECT 
            pay_week_start_monday AS week_start_monday,
            pay_iso_year_week AS iso_year_week,
            COALESCE(SUM(total_amount_payable), 0) AS amount,
            SUM(count_payments) AS items,
            SUM(count_drivers) AS drivers
        FROM ops.v_yango_receivable_payable
        WHERE {where_clause}
        GROUP BY pay_week_start_monday, pay_iso_year_week
        ORDER BY pay_week_start_monday DESC
    """)
    
    weeks_rows = db.execute(by_week_query, params).fetchall()
    by_week = [
        YangoByWeek(
            week_start_monday=row.week_start_monday,
            iso_year_week=row.iso_year_week,
            amount=Decimal(str(row.amount or 0)),
            items=row.items or 0,
            drivers=row.drivers or 0
        )
        for row in weeks_rows
    ]
    
    return YangoSummaryResponse(
        totals=totals,
        by_week=by_week
    )


@router.get("/yango/receivable_items", response_model=YangoReceivableItemsResponse)
def get_yango_receivable_items(
    db: Session = Depends(get_db),
    week_start_monday: Optional[date] = Query(None, description="Fecha inicio de semana"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Obtiene items de cobranza Yango con paginación.
    """
    # Construir condiciones WHERE
    where_conditions = ["1=1"]
    params = {"limit": limit, "offset": offset}
    
    if week_start_monday:
        where_conditions.append("pay_week_start_monday = :week_start_monday")
        params["week_start_monday"] = week_start_monday
    
    where_clause = " AND ".join(where_conditions)
    
    # Contar total
    count_query = text(f"""
        SELECT COUNT(*) AS total
        FROM ops.v_yango_receivable_payable_detail
        WHERE {where_clause}
    """)
    
    total = db.execute(count_query, params).scalar()
    
    # Obtener items
    items_query = text(f"""
        SELECT 
            pay_week_start_monday,
            pay_iso_year_week,
            payable_date,
            achieved_date,
            lead_date,
            lead_origin,
            payer,
            milestone_type,
            milestone_value,
            window_days,
            trips_in_window,
            person_key::text,
            driver_id,
            amount,
            currency,
            created_at_export
        FROM ops.v_yango_receivable_payable_detail
        WHERE {where_clause}
        ORDER BY pay_week_start_monday DESC, amount DESC
        LIMIT :limit OFFSET :offset
    """)
    
    rows = db.execute(items_query, params).fetchall()
    def to_date(value):
        """Convierte datetime a date si es necesario"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value
    
    items = [
        YangoReceivableItem(
            pay_week_start_monday=to_date(row.pay_week_start_monday),
            pay_iso_year_week=row.pay_iso_year_week,
            payable_date=to_date(row.payable_date),
            achieved_date=to_date(row.achieved_date),
            lead_date=to_date(row.lead_date),
            lead_origin=row.lead_origin,
            payer=row.payer,
            milestone_type=row.milestone_type,
            milestone_value=row.milestone_value,
            window_days=row.window_days,
            trips_in_window=row.trips_in_window,
            person_key=str(row.person_key) if row.person_key else None,
            driver_id=row.driver_id,
            amount=Decimal(str(row.amount or 0)),
            currency=row.currency,
            created_at_export=to_date(row.created_at_export)
        )
        for row in rows
    ]
    
    return YangoReceivableItemsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )
























