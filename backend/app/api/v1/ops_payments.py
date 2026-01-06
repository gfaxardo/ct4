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
    limit: int = Query(25, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 25. La vista es lenta, usa filtros restrictivos para evitar timeout."),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    order: OrderByOption = Query(OrderByOption.week_start_desc, description="Ordenamiento")
):
    """
    Obtiene la matriz de drivers con milestones M1/M5/M25 y estados Yango/window.
    
    Endpoint de presentación: usa vista materializada (ops.mv_payments_driver_matrix_cabinet) 
    si está disponible para mejor rendimiento, fallback a vista normal 
    (ops.v_payments_driver_matrix_cabinet) si no existe. No recalcula reglas de negocio.
    
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
        
        # Si no hay filtros, agregar filtros por defecto MUY restrictivos para evitar timeout
        # La vista es extremadamente lenta y necesita filtros agresivos
        if not where_conditions:
            where_conditions.append("origin_tag = 'cabinet'")
            params["origin_tag_default"] = 'cabinet'
            # Agregar filtro de fecha MUY reciente (última semana) para reducir dataset al mínimo
            from datetime import timedelta
            one_week_ago = date.today() - timedelta(days=7)
            where_conditions.append("week_start >= :week_start_from_default")
            params["week_start_from_default"] = one_week_ago
            # Reducir límite por defecto si no hay filtros
            if limit > 25:
                limit = 25
            logger.info(f"Sin filtros especificados, aplicando filtros por defecto MUY restrictivos: origin_tag='cabinet', week_start>={one_week_ago}, limit={limit}")
        
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
        
        # Determinar qué vista usar: materializada si existe, sino normal
        # Intentar detectar si existe la vista materializada
        view_name = "ops.v_payments_driver_matrix_cabinet"  # Default: vista normal
        try:
            # Verificar si existe la vista materializada
            check_mv_sql = """
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_payments_driver_matrix_cabinet'
                )
            """
            mv_exists = db.execute(text(check_mv_sql)).scalar()
            if mv_exists:
                view_name = "ops.mv_payments_driver_matrix_cabinet"
                logger.info("Usando vista materializada para mejor rendimiento")
            else:
                logger.info("Vista materializada no existe, usando vista normal")
        except Exception as e:
            logger.warning(f"No se pudo verificar vista materializada, usando vista normal: {str(e)}")
            view_name = "ops.v_payments_driver_matrix_cabinet"
        
        # Query para contar total (sin limit/offset)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {view_name}
            {where_clause}
        """
        
        # Query para obtener datos con ORDER BY y paginación
        sql = f"""
            SELECT *
            FROM {view_name}
            {where_clause}
            {order_by_clause}
            LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = limit
        params["offset"] = offset
        
        # Log SQL para debugging (solo en desarrollo)
        if logger.level <= logging.DEBUG:
            logger.debug(f"SQL ejecutado: {sql[:500]}...")
            logger.debug(f"Params: {params}")
        
        # Ejecutar query principal con manejo de timeout
        # Si falla, retornar error pero con mensaje claro
        rows = []
        try:
            result = db.execute(text(sql), params)
            rows = result.fetchall()
        except (ProgrammingError, OperationalError) as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "QueryCanceled" in error_msg or "canceling statement" in error_msg.lower():
                logger.error(f"Query principal timeout en driver-matrix. WHERE: {where_clause[:300]}, Params keys: {list(params.keys())}, Limit: {limit}, Error: {error_msg[:200]}")
                # Construir mensaje de error más útil con información de filtros aplicados
                applied_filters = []
                if "origin_tag" in str(where_clause):
                    applied_filters.append("origin_tag")
                if "week_start" in str(where_clause):
                    applied_filters.append("week_start")
                if "funnel_status" in str(where_clause):
                    applied_filters.append("funnel_status")
                if "only_pending" in str(where_clause) or only_pending:
                    applied_filters.append("only_pending")
                
                detail_msg = f"La vista es demasiado lenta incluso con filtros ({', '.join(applied_filters) if applied_filters else 'ninguno'}). "
                detail_msg += "La vista requiere optimización. Por ahora, usa filtros muy restrictivos: week_start_from reciente (última semana), funnel_status específico, only_pending=true, y límite máximo de 25."
                raise HTTPException(
                    status_code=503,
                    detail=detail_msg
                )
            else:
                # Otro error de SQL, re-raise
                raise
        
        # Ejecutar COUNT con manejo de timeout
        # Si el COUNT falla por timeout, usar aproximación basada en resultados
        total = None
        try:
            # Intentar COUNT (puede ser lento en vistas complejas)
            count_result = db.execute(text(count_sql), params)
            total = count_result.scalar() or 0
        except (ProgrammingError, OperationalError) as e:
            # Si falla el COUNT (timeout u otro error), usar aproximación
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "QueryCanceled" in error_msg or "canceling statement" in error_msg.lower():
                logger.warning(f"COUNT timeout en driver-matrix, usando aproximación: {error_msg[:200]}")
                # Aproximación inteligente:
                # - Si hay exactamente 'limit' resultados, probablemente hay más
                # - Si hay menos que 'limit', ese es el total real
                if len(rows) >= limit:
                    # Probablemente hay más resultados (mínimo estimado)
                    total = offset + len(rows) + 1
                else:
                    # Probablemente es el total real
                    total = offset + len(rows)
            else:
                # Otro error de SQL, loguear pero no fallar
                logger.warning(f"Error en COUNT (no timeout), usando aproximación: {error_msg[:200]}")
                # Usar misma aproximación
                if len(rows) >= limit:
                    total = offset + len(rows) + 1
                else:
                    total = offset + len(rows)
        
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

