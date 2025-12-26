"""
Endpoint READ-ONLY para consultar ops.v_payment_calculation

Ejemplo de uso:
GET /api/v1/payments/eligibility?is_payable=true&payable_from=2025-11-01&payable_to=2025-12-31&limit=50
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date
import logging

from app.db import get_db
from app.schemas.payments import (
    PaymentEligibilityRow,
    PaymentEligibilityResponse,
    OrderByField,
    OrderDirection
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/eligibility", response_model=PaymentEligibilityResponse)
def get_payment_eligibility(
    db: Session = Depends(get_db),
    origin_tag: Optional[str] = Query(None, description="Filtra por origin_tag: 'cabinet' o 'fleet_migration'"),
    rule_scope: Optional[str] = Query(None, description="Filtra por rule_scope: 'scout' o 'partner'"),
    is_payable: Optional[bool] = Query(None, description="Filtra por is_payable"),
    scout_id: Optional[int] = Query(None, description="Filtra por scout_id"),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id"),
    payable_from: Optional[date] = Query(None, description="Filtra por payable_date >= payable_from"),
    payable_to: Optional[date] = Query(None, description="Filtra por payable_date <= payable_to"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000)"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    order_by: OrderByField = Query(OrderByField.payable_date, description="Campo para ordenar"),
    order_dir: OrderDirection = Query(OrderDirection.asc, description="Dirección del ordenamiento")
):
    """
    Consulta la vista ops.v_payment_calculation con filtros opcionales.
    
    Todos los parámetros de filtro son opcionales. El endpoint retorna una lista paginada
    de registros que cumplen con los criterios especificados.
    
    Ejemplo:
    GET /api/v1/payments/eligibility?is_payable=true&payable_from=2025-11-01&payable_to=2025-12-31&limit=50
    """
    
    # Validar origin_tag si se proporciona
    if origin_tag is not None and origin_tag not in ['cabinet', 'fleet_migration']:
        raise HTTPException(
            status_code=400,
            detail=f"origin_tag debe ser 'cabinet' o 'fleet_migration', recibido: {origin_tag}"
        )
    
    # Validar rule_scope si se proporciona
    if rule_scope is not None and rule_scope not in ['scout', 'partner']:
        raise HTTPException(
            status_code=400,
            detail=f"rule_scope debe ser 'scout' o 'partner', recibido: {rule_scope}"
        )
    
    # Forzar casting explícito de limit y offset a int antes de usar
    limit = int(limit)
    offset = int(offset)
    
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    if origin_tag is not None:
        where_conditions.append("origin_tag = :origin_tag")
        params["origin_tag"] = origin_tag
    
    if rule_scope is not None:
        where_conditions.append("rule_scope = :rule_scope")
        params["rule_scope"] = rule_scope
    
    if is_payable is not None:
        where_conditions.append("is_payable = :is_payable")
        # Asegurar que is_payable sea boolean real antes de agregar a params
        params["is_payable"] = bool(is_payable)
    
    if scout_id is not None:
        where_conditions.append("scout_id = :scout_id")
        params["scout_id"] = scout_id
    
    if driver_id is not None:
        where_conditions.append("driver_id = :driver_id")
        params["driver_id"] = driver_id
    
    if payable_from is not None:
        where_conditions.append("payable_date >= :payable_from")
        params["payable_from"] = payable_from
    
    if payable_to is not None:
        where_conditions.append("payable_date <= :payable_to")
        params["payable_to"] = payable_to
    
    # Construir ORDER BY (whitelist estricta)
    order_by_field = order_by.value
    order_direction = order_dir.value
    
    # Validación adicional de seguridad (aunque ya está validado por el enum)
    allowed_order_fields = ['payable_date', 'lead_date', 'amount']
    if order_by_field not in allowed_order_fields:
        raise HTTPException(
            status_code=400,
            detail=f"order_by debe ser uno de {allowed_order_fields}, recibido: {order_by_field}"
        )
    
    if order_direction not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
            detail=f"order_dir debe ser 'asc' o 'desc', recibido: {order_direction}"
        )
    
    # Construir query SQL
    sql = "SELECT * FROM ops.v_payment_calculation WHERE 1=1"
    
    if where_conditions:
        sql += " AND " + " AND ".join(where_conditions)
    
    sql += f" ORDER BY {order_by_field} {order_direction}"
    sql += " LIMIT :limit OFFSET :offset"
    
    # Agregar limit y offset (ya convertidos a int) directamente
    # SQLAlchemy/psycopg2 manejará la conversión de tipos automáticamente
    params["limit"] = limit
    params["offset"] = offset
    
    # Logging (sin datos sensibles)
    log_filters = {
        "origin_tag": origin_tag,
        "rule_scope": rule_scope,
        "is_payable": is_payable,
        "scout_id": scout_id,
        "driver_id": driver_id,
        "payable_from": str(payable_from) if payable_from else None,
        "payable_to": str(payable_to) if payable_to else None,
        "limit": limit,
        "offset": offset,
        "order_by": order_by_field,
        "order_dir": order_direction
    }
    logger.info(f"payments eligibility query: {log_filters}")
    
    # Ejecutar query
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir a listas de dicts para Pydantic
        rows = [dict(row) for row in rows_data]
        
        # Construir respuesta
        filters_dict = {k: v for k, v in log_filters.items() if v is not None}
        
        return PaymentEligibilityResponse(
            status="ok",
            count=len(rows),
            filters=filters_dict,
            rows=[PaymentEligibilityRow(**row) for row in rows]
        )
    except Exception as e:
        logger.error(f"Error executing payment eligibility query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar elegibilidad de pagos: {str(e)}"
        )

