"""
Endpoint READ-ONLY para consultar ops.v_payment_calculation

Ejemplo de uso:
GET /api/v1/payments/eligibility?is_payable=true&payable_from=2025-11-01&payable_to=2025-12-31&limit=50
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal
import logging
import csv
import io

from app.db import get_db
from app.schemas.payments import (
    PaymentEligibilityRow,
    PaymentEligibilityResponse,
    OrderByField,
    OrderDirection,
    DriverMatrixRow,
    DriverMatrixResponse,
    DriverMatrixMeta,
    DriverMatrixTotals
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
        
        # Convertir a listas de dicts para Pydantic, convirtiendo UUIDs a strings
        def convert_uuids_to_strings(row_dict):
            """Convierte UUIDs a strings para compatibilidad con Pydantic"""
            converted = {}
            for key, value in row_dict.items():
                if isinstance(value, UUID):
                    converted[key] = str(value)
                else:
                    converted[key] = value
            return converted
        
        rows = [convert_uuids_to_strings(dict(row)) for row in rows_data]
        
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


@router.get("/driver-matrix", response_model=DriverMatrixResponse)
def get_driver_matrix(
    db: Session = Depends(get_db),
    week_from: Optional[date] = Query(None, description="Filtra por week_start >= week_from"),
    week_to: Optional[date] = Query(None, description="Filtra por week_start <= week_to"),
    search: Optional[str] = Query(None, description="Busca por driver_id, person_key, driver_name"),
    only_pending: Optional[bool] = Query(None, description="Filtra drivers con algún milestone pendiente"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(50, ge=1, le=500, description="Límite de resultados por página (máx 500)")
):
    """
    Obtiene la matriz de drivers con milestones M1/M5/M25 y estados Yango/Scout.
    
    Filtros:
    - week_from/week_to: Filtrar por semana (week_start)
    - search: Buscar por driver_id, person_key o driver_name
    - only_pending: Si true, solo drivers con algún milestone pendiente (no PAID o con overdue_days > 0)
    - page/limit: Paginación
    
    Respuesta incluye:
    - rows: Lista de drivers con sus milestones
    - meta: Metadatos de paginación
    - totals: Totales agregados (drivers, montos, counts)
    """
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    if week_from:
        where_conditions.append("week_start >= :week_from")
        params["week_from"] = week_from
    
    if week_to:
        where_conditions.append("week_start <= :week_to")
        params["week_to"] = week_to
    
    if search:
        # Buscar en driver_id, person_key, driver_name
        where_conditions.append("""
            (driver_id::text ILIKE :search 
             OR person_key::text ILIKE :search 
             OR driver_name ILIKE :search)
        """)
        params["search"] = f"%{search}%"
    
    if only_pending:
        # Considera "pendiente" si existe alguno de estos:
        # - (m1_yango_payment_status != 'PAID' AND m1_achieved_flag = true)
        # - o (m5_yango_payment_status != 'PAID' AND m5_achieved_flag = true)
        # - o (m25_yango_payment_status != 'PAID' AND m25_achieved_flag = true)
        # - o (m1_overdue_days > 0 OR m5_overdue_days > 0 OR m25_overdue_days > 0)
        where_conditions.append("""
            (
                (m1_achieved_flag = true AND COALESCE(m1_yango_payment_status, '') != 'PAID')
                OR (m5_achieved_flag = true AND COALESCE(m5_yango_payment_status, '') != 'PAID')
                OR (m25_achieved_flag = true AND COALESCE(m25_yango_payment_status, '') != 'PAID')
                OR (COALESCE(m1_overdue_days, 0) > 0)
                OR (COALESCE(m5_overdue_days, 0) > 0)
                OR (COALESCE(m25_overdue_days, 0) > 0)
            )
        """)
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Calcular offset desde page
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_payments_driver_matrix_cabinet
        {where_clause}
    """
    
    # Query para obtener datos con ORDER BY
    sql = f"""
        SELECT *
        FROM ops.v_payments_driver_matrix_cabinet
        {where_clause}
        ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """
    
    # Query para obtener totals
    totals_sql = f"""
        SELECT 
            COUNT(*) AS drivers,
            COALESCE(SUM(
                COALESCE(m1_expected_amount_yango, 0) +
                COALESCE(m5_expected_amount_yango, 0) +
                COALESCE(m25_expected_amount_yango, 0)
            ), 0) AS expected_yango_sum,
            COALESCE(SUM(
                CASE WHEN m1_yango_payment_status = 'PAID' THEN COALESCE(m1_expected_amount_yango, 0) ELSE 0 END +
                CASE WHEN m5_yango_payment_status = 'PAID' THEN COALESCE(m5_expected_amount_yango, 0) ELSE 0 END +
                CASE WHEN m25_yango_payment_status = 'PAID' THEN COALESCE(m25_expected_amount_yango, 0) ELSE 0 END
            ), 0) AS paid_sum,
            COALESCE(SUM(
                CASE WHEN m1_yango_payment_status != 'PAID' AND m1_achieved_flag = true THEN COALESCE(m1_expected_amount_yango, 0) ELSE 0 END +
                CASE WHEN m5_yango_payment_status != 'PAID' AND m5_achieved_flag = true THEN COALESCE(m5_expected_amount_yango, 0) ELSE 0 END +
                CASE WHEN m25_yango_payment_status != 'PAID' AND m25_achieved_flag = true THEN COALESCE(m25_expected_amount_yango, 0) ELSE 0 END
            ), 0) AS receivable_sum,
            COUNT(*) FILTER (
                WHERE m1_window_status = 'expired' 
                OR m5_window_status = 'expired' 
                OR m25_window_status = 'expired'
            ) AS expired_count,
            COUNT(*) FILTER (
                WHERE m1_window_status = 'in_window' 
                OR m5_window_status = 'in_window' 
                OR m25_window_status = 'in_window'
            ) AS in_window_count
        FROM ops.v_payments_driver_matrix_cabinet
        {where_clause}
    """
    
    try:
        # Obtener total
        count_result = db.execute(text(count_sql), params).fetchone()
        total_rows = count_result.total if count_result else 0
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir UUIDs a strings
        def convert_uuids_to_strings(row_dict):
            converted = {}
            for key, value in row_dict.items():
                if isinstance(value, UUID):
                    converted[key] = str(value)
                else:
                    converted[key] = value
            return converted
        
        rows = [DriverMatrixRow(**convert_uuids_to_strings(dict(row))) for row in rows_data]
        
        # Obtener totals (sin paginación)
        totals_result = db.execute(text(totals_sql), {k: v for k, v in params.items() if k not in ['limit', 'offset']}).fetchone()
        
        totals = DriverMatrixTotals(
            drivers=total_rows,
            expected_yango_sum=Decimal(str(totals_result.expected_yango_sum)) if totals_result else Decimal('0'),
            paid_sum=Decimal(str(totals_result.paid_sum)) if totals_result else Decimal('0'),
            receivable_sum=Decimal(str(totals_result.receivable_sum)) if totals_result else Decimal('0'),
            expired_count=totals_result.expired_count if totals_result else 0,
            in_window_count=totals_result.in_window_count if totals_result else 0
        )
        
        meta = DriverMatrixMeta(
            page=page,
            limit=limit,
            total_rows=total_rows
        )
        
        return DriverMatrixResponse(
            rows=rows,
            meta=meta,
            totals=totals
        )
    except ProgrammingError as e:
        logger.error(f"Error SQL en driver-matrix: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar matriz de drivers: {str(e)}"
        )
    except OperationalError as e:
        logger.error(f"Error de conexión en driver-matrix: {e}")
        raise HTTPException(
            status_code=503,
            detail="DB no disponible / revisa DATABASE_URL"
        )
    except Exception as e:
        logger.error(f"Error inesperado en driver-matrix: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar matriz de drivers: {str(e)}"
        )


@router.get("/driver-matrix/export")
def export_driver_matrix(
    db: Session = Depends(get_db),
    week_from: Optional[date] = Query(None, description="Filtra por week_start >= week_from"),
    week_to: Optional[date] = Query(None, description="Filtra por week_start <= week_to"),
    search: Optional[str] = Query(None, description="Busca por driver_id, person_key, driver_name"),
    only_pending: Optional[bool] = Query(None, description="Filtra drivers con algún milestone pendiente")
):
    """
    Exporta la matriz de drivers a CSV con BOM UTF-8.
    
    Mismos filtros que /driver-matrix pero sin paginación.
    Retorna CSV con todas las columnas de la vista.
    """
    # Construir WHERE dinámico (mismo que en get_driver_matrix)
    where_conditions = []
    params = {}
    
    if week_from:
        where_conditions.append("week_start >= :week_from")
        params["week_from"] = week_from
    
    if week_to:
        where_conditions.append("week_start <= :week_to")
        params["week_to"] = week_to
    
    if search:
        where_conditions.append("""
            (driver_id::text ILIKE :search 
             OR person_key::text ILIKE :search 
             OR driver_name ILIKE :search)
        """)
        params["search"] = f"%{search}%"
    
    if only_pending:
        where_conditions.append("""
            (
                (m1_achieved_flag = true AND COALESCE(m1_yango_payment_status, '') != 'PAID')
                OR (m5_achieved_flag = true AND COALESCE(m5_yango_payment_status, '') != 'PAID')
                OR (m25_achieved_flag = true AND COALESCE(m25_yango_payment_status, '') != 'PAID')
                OR (COALESCE(m1_overdue_days, 0) > 0)
                OR (COALESCE(m5_overdue_days, 0) > 0)
                OR (COALESCE(m25_overdue_days, 0) > 0)
            )
        """)
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Query para obtener todos los datos (sin paginación)
    sql = f"""
        SELECT *
        FROM ops.v_payments_driver_matrix_cabinet
        {where_clause}
        ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST
    """
    
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        if not rows_data:
            # Retornar CSV vacío con headers
            output = io.StringIO()
            fieldnames = [
                "driver_id", "person_key", "driver_name", "lead_date", "week_start", "origin_tag",
                "connected_flag", "connected_date",
                "m1_achieved_flag", "m1_achieved_date", "m1_expected_amount_yango", "m1_yango_payment_status",
                "m1_window_status", "m1_overdue_days",
                "m5_achieved_flag", "m5_achieved_date", "m5_expected_amount_yango", "m5_yango_payment_status",
                "m5_window_status", "m5_overdue_days",
                "m25_achieved_flag", "m25_achieved_date", "m25_expected_amount_yango", "m25_yango_payment_status",
                "m25_window_status", "m25_overdue_days",
                "scout_due_flag", "scout_paid_flag", "scout_amount"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
        else:
            # Convertir a dicts y escribir CSV
            output = io.StringIO()
            fieldnames = list(rows_data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in rows_data:
                row_dict = dict(row)
                # Convertir UUIDs a strings
                for key, value in row_dict.items():
                    if isinstance(value, UUID):
                        row_dict[key] = str(value)
                    elif value is None:
                        row_dict[key] = ""
                writer.writerow(row_dict)
        
        csv_content = output.getvalue()
        output.close()
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"driver_matrix_{timestamp}.csv"
        
        # Codificar CSV a bytes UTF-8
        csv_bytes = csv_content.encode('utf-8')
        
        # Agregar BOM UTF-8-SIG (EF BB BF) al inicio
        bom_bytes = b'\xef\xbb\xbf'
        csv_content_with_bom = bom_bytes + csv_bytes
        
        return Response(
            content=csv_content_with_bom,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except ProgrammingError as e:
        logger.error(f"Error SQL en driver-matrix export: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar matriz de drivers: {str(e)}"
        )
    except OperationalError as e:
        logger.error(f"Error de conexión en driver-matrix export: {e}")
        raise HTTPException(
            status_code=503,
            detail="DB no disponible / revisa DATABASE_URL"
        )
    except Exception as e:
        logger.error(f"Error inesperado en driver-matrix export: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar matriz de drivers: {str(e)}"
        )

