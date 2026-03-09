"""
Lógica de negocio: driver matrix (ops payments).
"""
import logging
from datetime import date
from enum import Enum
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_utils import row_to_dict
from app.services.mv_cache import get_best_view
from app.schemas.payments import (
    DriverMatrixRow,
    OpsDriverMatrixResponse,
    OpsDriverMatrixMeta,
)

logger = logging.getLogger(__name__)


class OrderByOption(str, Enum):
    week_start_desc = "week_start_desc"
    week_start_asc = "week_start_asc"
    lead_date_desc = "lead_date_desc"
    lead_date_asc = "lead_date_asc"


def get_driver_matrix(
    db: Session,
    *,
    week_start_from: Optional[date] = None,
    week_start_to: Optional[date] = None,
    origin_tag: Optional[str] = None,
    funnel_status: Optional[str] = None,
    only_pending: bool = False,
    limit: int = 200,
    offset: int = 0,
    order: OrderByOption = OrderByOption.week_start_desc,
) -> OpsDriverMatrixResponse:
    """
    Obtiene la matriz de drivers con milestones M1/M5/M25 y estados Yango/window.
    Usa vista materializada si existe, sino vista normal.
    """
    where_conditions = []
    params: dict = {}

    if week_start_from:
        where_conditions.append("lead_date >= :week_start_from")
        params["week_start_from"] = week_start_from
    if week_start_to:
        where_conditions.append("lead_date <= :week_start_to")
        params["week_start_to"] = week_start_to
    if origin_tag and origin_tag.lower() not in ("all", ""):
        if origin_tag not in ("cabinet", "fleet_migration", "unknown"):
            raise HTTPException(
                status_code=400,
                detail=f"origin_tag debe ser 'cabinet', 'fleet_migration', 'unknown' o 'All', recibido: {origin_tag}",
            )
        where_conditions.append("origin_tag = :origin_tag")
        params["origin_tag"] = origin_tag
    if funnel_status:
        logger.info("Filtro funnel_status=%s ignorado (no disponible en vista actual)", funnel_status)
    if only_pending:
        where_conditions.append("is_payable = true")

    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    view_name = get_best_view(
        db,
        "ops",
        ["mv_payments_driver_matrix_cabinet", "mv_payment_calculation"],
        "ops.v_payment_calculation",
    )
    try:
        check_result = db.execute(text(f"SELECT * FROM {view_name} LIMIT 0"))
        columns = list(check_result.keys())
        if len(columns) <= 1 and columns and columns[0] == "dummy":
            logger.warning("%s es un placeholder, usando v_payment_calculation", view_name)
            view_name = "ops.v_payment_calculation"
    except Exception as e:
        logger.warning("Error verificando vista %s: %s", view_name, e)

    if order == OrderByOption.week_start_desc:
        order_by_clause = "ORDER BY lead_date DESC NULLS LAST, driver_id ASC NULLS LAST"
    elif order == OrderByOption.week_start_asc:
        order_by_clause = "ORDER BY lead_date ASC NULLS LAST, driver_id ASC NULLS LAST"
    elif order == OrderByOption.lead_date_desc:
        order_by_clause = "ORDER BY lead_date DESC NULLS LAST, driver_id ASC NULLS LAST"
    elif order == OrderByOption.lead_date_asc:
        order_by_clause = "ORDER BY lead_date ASC NULLS LAST, driver_id ASC NULLS LAST"
    else:
        order_by_clause = "ORDER BY lead_date DESC NULLS LAST, driver_id ASC NULLS LAST"

    count_sql = f"SELECT COUNT(*) AS total FROM {view_name} {where_clause}"
    sql = f"""
        SELECT * FROM {view_name}
        {where_clause}
        {order_by_clause}
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    rows = []
    try:
        result = db.execute(text(sql), params)
        rows = result.fetchall()
    except (ProgrammingError, OperationalError) as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "QueryCanceled" in error_msg or "canceling statement" in error_msg.lower():
            applied_filters = []
            if "origin_tag" in str(where_clause):
                applied_filters.append("origin_tag")
            if "week_start" in str(where_clause):
                applied_filters.append("week_start")
            if only_pending:
                applied_filters.append("only_pending")
            detail_msg = (
                f"La vista es demasiado lenta incluso con filtros ({', '.join(applied_filters) or 'ninguno'}). "
                "Usa filtros más restrictivos."
            )
            raise HTTPException(status_code=503, detail=detail_msg) from e
        raise

    total = None
    try:
        count_result = db.execute(text(count_sql), params)
        total = count_result.scalar() or 0
    except (ProgrammingError, OperationalError) as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "QueryCanceled" in error_msg or "canceling statement" in error_msg.lower():
            total = offset + len(rows) + 1 if len(rows) >= limit else offset + len(rows)
        else:
            total = offset + len(rows) + 1 if len(rows) >= limit else offset + len(rows)

    data = []
    for row in rows:
        row_dict = row_to_dict(row)
        if "milestone_trips" in row_dict:
            milestone = row_dict.get("milestone_trips")
            mapped = {
                "driver_id": row_dict.get("driver_id"),
                "person_key": row_dict.get("person_key"),
                "lead_date": row_dict.get("lead_date"),
                "origin_tag": row_dict.get("origin_tag"),
                "highest_milestone": milestone,
                "m1_achieved_flag": milestone == 1 and row_dict.get("milestone_achieved"),
                "m1_achieved_date": row_dict.get("achieved_date") if milestone == 1 else None,
                "m1_expected_amount_yango": row_dict.get("amount") if milestone == 1 else None,
                "m5_achieved_flag": milestone == 5 and row_dict.get("milestone_achieved"),
                "m5_achieved_date": row_dict.get("achieved_date") if milestone == 5 else None,
                "m5_expected_amount_yango": row_dict.get("amount") if milestone == 5 else None,
                "m25_achieved_flag": milestone == 25 and row_dict.get("milestone_achieved"),
                "m25_achieved_date": row_dict.get("achieved_date") if milestone == 25 else None,
                "m25_expected_amount_yango": row_dict.get("amount") if milestone == 25 else None,
            }
            data.append(DriverMatrixRow.model_validate(mapped))
        else:
            data.append(DriverMatrixRow.model_validate(row_dict))

    meta = OpsDriverMatrixMeta(limit=limit, offset=offset, returned=len(data), total=total)
    return OpsDriverMatrixResponse(meta=meta, data=data)
