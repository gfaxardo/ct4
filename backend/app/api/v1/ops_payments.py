"""
Endpoints para operaciones de payments dentro del módulo ops
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError
from typing import Optional
from datetime import date
from enum import Enum
import logging

from app.db import get_db
from app.schemas.payments import (
    DriverMatrixRow,
    OpsDriverMatrixResponse,
    OpsDriverMatrixMeta
)

logger = logging.getLogger(__name__)
router = APIRouter()


class OrderByOption(str, Enum):
    week_start_desc = "week_start_desc"
    week_start_asc = "week_start_asc"
    lead_date_desc = "lead_date_desc"
    lead_date_asc = "lead_date_asc"


@router.get("/driver-matrix", response_model=OpsDriverMatrixResponse)
def get_driver_matrix(
    db: Session = Depends(get_db),
    week_start_from: Optional[date] = Query(None, description="Filtra por week_start >= week_start_from (inclusive)"),
    week_start_to: Optional[date] = Query(None, description="Filtra por week_start <= week_start_to (inclusive)"),
    origin_tag: Optional[str] = Query(None, description="Filtra por origin_tag: 'cabinet', 'fleet_migration', 'unknown' o 'All'"),
    funnel_status: Optional[str] = Query(None, description="Filtra por funnel_status: 'registered_incomplete', 'registered_complete', 'connected_no_trips', 'reached_m1', 'reached_m5', 'reached_m25'"),
    only_pending: bool = Query(False, description="Si true, solo drivers con al menos 1 milestone pendiente"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000)"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    order: OrderByOption = Query(OrderByOption.week_start_desc, description="Ordenamiento")
):
    """
    Obtiene la matriz de drivers con milestones M1/M5/M25 y estados Yango/window.
    
    Endpoint de presentación: solo SELECT sobre la vista ops.v_payments_driver_matrix_cabinet.
    No recalcula reglas de negocio.
    
    Filtros:
    - week_start_from/week_start_to: Filtrar por semana (week_start) inclusive
    - origin_tag: Filtrar por origen ('cabinet' o 'fleet_migration')
    - only_pending: Si true, solo drivers con al menos 1 milestone achieved cuyo yango_payment_status != 'PAID'
    - limit/offset: Paginación
    - order: Ordenamiento (week_start_desc, week_start_asc, lead_date_desc, lead_date_asc)
    
    Respuesta incluye:
    - meta: Metadatos de paginación (limit, offset, returned, total)
    - data: Lista de drivers con sus milestones
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=200&offset=0"
    ```
    
    Ejemplo curl (con filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/payments/driver-matrix?week_start_from=2025-01-01&week_start_to=2025-12-31&origin_tag=cabinet&only_pending=true&limit=100&offset=0&order=week_start_desc"
    ```
    """
    try:
        # Construir WHERE dinámico
        where_conditions = []
        params = {}
        
        if week_start_from:
            where_conditions.append("week_start >= :week_start_from")
            params["week_start_from"] = week_start_from
        
        if week_start_to:
            where_conditions.append("week_start <= :week_start_to")
            params["week_start_to"] = week_start_to
        
        if origin_tag:
            # Validar que sea uno de los valores permitidos
            # 'All' o vacío => no filtra
            if origin_tag.lower() == 'all' or origin_tag == '':
                # No agregar filtro
                pass
            elif origin_tag in ('cabinet', 'fleet_migration', 'unknown'):
                where_conditions.append("origin_tag = :origin_tag")
                params["origin_tag"] = origin_tag
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"origin_tag debe ser 'cabinet', 'fleet_migration', 'unknown' o 'All', recibido: {origin_tag}"
                )
        
        if funnel_status:
            # Validar que sea uno de los valores permitidos
            valid_funnel_statuses = ('registered_incomplete', 'registered_complete', 'connected_no_trips', 'reached_m1', 'reached_m5', 'reached_m25')
            if funnel_status in valid_funnel_statuses:
                where_conditions.append("funnel_status = :funnel_status")
                params["funnel_status"] = funnel_status
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"funnel_status debe ser uno de {valid_funnel_statuses}, recibido: {funnel_status}"
                )
        
        if only_pending:
            # Incluir fila si existe al menos 1 milestone achieved cuyo yango_payment_status != 'PAID'
            # Considerar NULL como pendiente (o sea, != 'PAID' también)
            where_conditions.append("""
                (
                    (m1_achieved_flag = true AND COALESCE(m1_yango_payment_status, '') != 'PAID')
                    OR (m5_achieved_flag = true AND COALESCE(m5_yango_payment_status, '') != 'PAID')
                    OR (m25_achieved_flag = true AND COALESCE(m25_yango_payment_status, '') != 'PAID')
                )
            """)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Construir ORDER BY según el parámetro order
        order_by_clause = ""
        if order == OrderByOption.week_start_desc:
            order_by_clause = "ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST"
        elif order == OrderByOption.week_start_asc:
            order_by_clause = "ORDER BY week_start ASC NULLS LAST, driver_name ASC NULLS LAST"
        elif order == OrderByOption.lead_date_desc:
            order_by_clause = "ORDER BY lead_date DESC NULLS LAST, driver_name ASC NULLS LAST"
        elif order == OrderByOption.lead_date_asc:
            order_by_clause = "ORDER BY lead_date ASC NULLS LAST, driver_name ASC NULLS LAST"
        else:
            # Default fallback
            order_by_clause = "ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST"
        
        # Query para contar total (sin limit/offset)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM ops.v_payments_driver_matrix_cabinet
            {where_clause}
        """
        
        # Query para obtener datos con ORDER BY y paginación
        sql = f"""
            SELECT *
            FROM ops.v_payments_driver_matrix_cabinet
            {where_clause}
            {order_by_clause}
            LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = limit
        params["offset"] = offset
        
        # Ejecutar COUNT
        count_result = db.execute(text(count_sql), params)
        total = count_result.scalar() or 0
        
        # Ejecutar query principal
        result = db.execute(text(sql), params)
        rows = result.fetchall()
        
        # Convertir a schemas
        data = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            data.append(DriverMatrixRow.model_validate(row_dict))
        
        # Construir respuesta
        returned = len(data)
        meta = OpsDriverMatrixMeta(
            limit=limit,
            offset=offset,
            returned=returned,
            total=total
        )
        
        return OpsDriverMatrixResponse(
            meta=meta,
            data=data
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (400, etc.)
        raise
    except (ProgrammingError, OperationalError) as e:
        # Errores de SQL (vista no existe, etc.)
        logger.error(f"Error de base de datos en get_driver_matrix: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )
    except Exception as e:
        # Otros errores inesperados
        logger.error(f"Error inesperado en get_driver_matrix: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="internal_server_error"
        )

