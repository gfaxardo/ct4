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
from app.schemas.cabinet_financial import (
    CabinetFinancialRow,
    CabinetFinancialResponse,
    CabinetFinancialSummary,
    CabinetFinancialSummaryTotal,
    CabinetFinancialMeta
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
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 200."),
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


@router.get("/cabinet-financial-14d", response_model=CabinetFinancialResponse)
def get_cabinet_financial_14d(
    db: Session = Depends(get_db),
    only_with_debt: bool = Query(False, description="Si true, solo drivers con deuda pendiente (amount_due_yango > 0)"),
    min_debt: Optional[float] = Query(None, ge=0, description="Filtra por deuda mínima (amount_due_yango >= min_debt)"),
    reached_milestone: Optional[str] = Query(None, description="Filtra por milestone alcanzado: 'm1', 'm5', 'm25'"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 200."),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    include_summary: bool = Query(True, description="Incluir resumen ejecutivo en la respuesta"),
    use_materialized: bool = Query(True, description="Usar vista materializada para mejor rendimiento")
):
    """
    Obtiene la fuente de verdad financiera para CABINET (ventana de 14 días).
    
    Esta vista permite determinar con exactitud qué conductores generan pago de Yango
    y detectar deudas por milestones no pagados.
    
    Filtros:
    - only_with_debt: Solo drivers con deuda pendiente (amount_due_yango > 0)
    - min_debt: Filtra por deuda mínima
    - reached_milestone: Filtra por milestone alcanzado ('m1', 'm5', 'm25')
    - limit/offset: Paginación
    - include_summary: Incluir resumen ejecutivo
    - use_materialized: Usar vista materializada (mejor rendimiento, datos pueden estar desactualizados)
    
    Respuesta incluye:
    - meta: Metadatos de paginación
    - summary: Resumen ejecutivo (total esperado, pagado, deuda, porcentaje de cobranza)
    - data: Lista de drivers con información financiera
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?only_with_debt=true&limit=50"
    ```
    """
    try:
        # Seleccionar vista (materializada o normal)
        # Verificar si la vista materializada existe
        if use_materialized:
            check_mv = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_cabinet_financial_14d'
                )
            """))
            mv_exists = check_mv.scalar()
            view_name = "ops.mv_cabinet_financial_14d" if mv_exists else "ops.v_cabinet_financial_14d"
            
            # #region agent log
            import json
            from datetime import datetime
            try:
                log_entry = {
                    "id": f"log_{int(datetime.now().timestamp() * 1000)}",
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": "ops_payments.py:get_cabinet_financial_14d",
                    "message": "VIEW_SELECTED",
                    "data": {"view_name": view_name, "mv_exists": mv_exists, "use_materialized": use_materialized},
                    "sessionId": "debug-session",
                    "runId": "api-request",
                    "hypothesisId": "H4"
                }
                with open("c:\\cursor\\CT4\\.cursor\\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception:
                pass
            # #endregion
        else:
            view_name = "ops.v_cabinet_financial_14d"
        
        # Construir WHERE dinámico
        where_conditions = []
        params = {}
        
        if only_with_debt:
            where_conditions.append("amount_due_yango > 0")
        
        if min_debt is not None:
            where_conditions.append("amount_due_yango >= :min_debt")
            params["min_debt"] = min_debt
        
        if reached_milestone:
            milestone_lower = reached_milestone.lower()
            if milestone_lower == 'm1':
                # M1: alcanzó M1 pero NO alcanzó M5 (solo M1)
                where_conditions.append("reached_m1_14d = true AND reached_m5_14d = false")
            elif milestone_lower == 'm5':
                # M5: alcanzó M5 pero NO alcanzó M25 (solo M5, o M1+M5)
                where_conditions.append("reached_m5_14d = true AND reached_m25_14d = false")
            elif milestone_lower == 'm25':
                # M25: alcanzó M25 (puede haber alcanzado M1 y M5 también)
                where_conditions.append("reached_m25_14d = true")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"reached_milestone debe ser 'm1', 'm5' o 'm25', recibido: {reached_milestone}"
                )
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Query principal
        query_sql = f"""
            SELECT 
                driver_id,
                driver_name,
                lead_date,
                iso_week,
                connected_flag,
                connected_date,
                total_trips_14d,
                reached_m1_14d,
                reached_m5_14d,
                reached_m25_14d,
                expected_amount_m1,
                expected_amount_m5,
                expected_amount_m25,
                expected_total_yango,
                claim_m1_exists,
                claim_m1_paid,
                claim_m5_exists,
                claim_m5_paid,
                claim_m25_exists,
                claim_m25_paid,
                paid_amount_m1,
                paid_amount_m5,
                paid_amount_m25,
                total_paid_yango,
                amount_due_yango
            FROM {view_name}
            WHERE {where_clause}
            ORDER BY lead_date DESC NULLS LAST, driver_id
            LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = limit
        params["offset"] = offset
        
        # #region agent log
        import json
        from datetime import datetime
        try:
            # Verificar max lead_date en la vista
            max_date_query = f"SELECT MAX(lead_date) AS max_date FROM {view_name}"
            max_date_result = db.execute(text(max_date_query))
            max_date = max_date_result.scalar()
            
            log_entry = {
                "id": f"log_{int(datetime.now().timestamp() * 1000)}",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "location": "ops_payments.py:get_cabinet_financial_14d",
                "message": "BEFORE_QUERY",
                "data": {"view_name": view_name, "max_lead_date": str(max_date) if max_date else None},
                "sessionId": "debug-session",
                "runId": "api-request",
                "hypothesisId": "H4"
            }
            with open("c:\\cursor\\CT4\\.cursor\\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Ejecutar query
        result = db.execute(text(query_sql), params)
        rows = result.fetchall()
        
        # #region agent log
        try:
            log_entry = {
                "id": f"log_{int(datetime.now().timestamp() * 1000)}",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "location": "ops_payments.py:get_cabinet_financial_14d",
                "message": "AFTER_QUERY",
                "data": {"rows_returned": len(rows), "view_name": view_name},
                "sessionId": "debug-session",
                "runId": "api-request",
                "hypothesisId": "H4"
            }
            with open("c:\\cursor\\CT4\\.cursor\\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Convertir a schemas
        data = [CabinetFinancialRow(
            driver_id=row.driver_id,
            driver_name=getattr(row, 'driver_name', None),
            lead_date=row.lead_date,
            iso_week=getattr(row, 'iso_week', None),
            connected_flag=row.connected_flag,
            connected_date=row.connected_date,
            total_trips_14d=row.total_trips_14d,
            reached_m1_14d=row.reached_m1_14d,
            reached_m5_14d=row.reached_m5_14d,
            reached_m25_14d=row.reached_m25_14d,
            expected_amount_m1=row.expected_amount_m1,
            expected_amount_m5=row.expected_amount_m5,
            expected_amount_m25=row.expected_amount_m25,
            expected_total_yango=row.expected_total_yango,
            claim_m1_exists=row.claim_m1_exists,
            claim_m1_paid=row.claim_m1_paid,
            claim_m5_exists=row.claim_m5_exists,
            claim_m5_paid=row.claim_m5_paid,
            claim_m25_exists=row.claim_m25_exists,
            claim_m25_paid=row.claim_m25_paid,
            paid_amount_m1=row.paid_amount_m1,
            paid_amount_m5=row.paid_amount_m5,
            paid_amount_m25=row.paid_amount_m25,
            total_paid_yango=row.total_paid_yango,
            amount_due_yango=row.amount_due_yango
        ) for row in rows]
        
        # COUNT para total
        count_sql = f"SELECT COUNT(*) FROM {view_name} WHERE {where_clause}"
        count_result = db.execute(text(count_sql), {k: v for k, v in params.items() if k not in ['limit', 'offset']})
        total = count_result.scalar() or 0
        
        # Resumen ejecutivo (si se solicita)
        summary = None
        summary_total = None
        if include_summary:
            # Resumen con filtros aplicados
            summary_sql = f"""
                SELECT 
                    COUNT(*) AS total_drivers,
                    COUNT(CASE WHEN expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
                    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
                    COALESCE(SUM(expected_total_yango), 0) AS total_expected_yango,
                    COALESCE(SUM(total_paid_yango), 0) AS total_paid_yango,
                    COALESCE(SUM(amount_due_yango), 0) AS total_debt_yango,
                    CASE 
                        WHEN SUM(expected_total_yango) > 0 
                        THEN ROUND((SUM(total_paid_yango) / SUM(expected_total_yango)) * 100, 2)
                        ELSE 0
                    END AS collection_percentage,
                    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_m1,
                    COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS drivers_m5,
                    COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS drivers_m25
                FROM {view_name}
                WHERE {where_clause}
            """
            summary_result = db.execute(text(summary_sql), {k: v for k, v in params.items() if k not in ['limit', 'offset']})
            summary_row = summary_result.fetchone()
            
            if summary_row:
                summary = CabinetFinancialSummary(
                    total_drivers=summary_row.total_drivers,
                    drivers_with_expected=summary_row.drivers_with_expected,
                    drivers_with_debt=summary_row.drivers_with_debt,
                    total_expected_yango=summary_row.total_expected_yango,
                    total_paid_yango=summary_row.total_paid_yango,
                    total_debt_yango=summary_row.total_debt_yango,
                    collection_percentage=float(summary_row.collection_percentage),
                    drivers_m1=summary_row.drivers_m1,
                    drivers_m5=summary_row.drivers_m5,
                    drivers_m25=summary_row.drivers_m25
                )
            
            # Resumen total sin filtros (siempre calcular para contexto)
            summary_total_sql = f"""
                SELECT 
                    COUNT(*) AS total_drivers,
                    COUNT(CASE WHEN expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
                    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
                    COALESCE(SUM(expected_total_yango), 0) AS total_expected_yango,
                    COALESCE(SUM(total_paid_yango), 0) AS total_paid_yango,
                    COALESCE(SUM(amount_due_yango), 0) AS total_debt_yango,
                    CASE 
                        WHEN SUM(expected_total_yango) > 0 
                        THEN ROUND((SUM(total_paid_yango) / SUM(expected_total_yango)) * 100, 2)
                        ELSE 0
                    END AS collection_percentage,
                    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_m1,
                    COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS drivers_m5,
                    COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS drivers_m25
                FROM {view_name}
            """
            summary_total_result = db.execute(text(summary_total_sql))
            summary_total_row = summary_total_result.fetchone()
            
            if summary_total_row:
                summary_total = CabinetFinancialSummaryTotal(
                    total_drivers=summary_total_row.total_drivers,
                    drivers_with_expected=summary_total_row.drivers_with_expected,
                    drivers_with_debt=summary_total_row.drivers_with_debt,
                    total_expected_yango=summary_total_row.total_expected_yango,
                    total_paid_yango=summary_total_row.total_paid_yango,
                    total_debt_yango=summary_total_row.total_debt_yango,
                    collection_percentage=float(summary_total_row.collection_percentage),
                    drivers_m1=summary_total_row.drivers_m1,
                    drivers_m5=summary_total_row.drivers_m5,
                    drivers_m25=summary_total_row.drivers_m25
                )
        
        # Metadatos
        meta = CabinetFinancialMeta(
            limit=limit,
            offset=offset,
            returned=len(data),
            total=total
        )
        
        return CabinetFinancialResponse(
            meta=meta,
            summary=summary,
            summary_total=summary_total,
            data=data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en get_cabinet_financial_14d: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

