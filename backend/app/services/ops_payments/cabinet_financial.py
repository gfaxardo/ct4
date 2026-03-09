"""
Lógica de negocio: cabinet financial 14d, funnel gap, KPI red recovery, claims audit.
"""
import logging
from datetime import date
from time import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.kpi_red_recovery import (
    KpiRedRecoveryMetricsResponse,
    KpiRedRecoveryMetricsDaily,
)

logger = logging.getLogger(__name__)

CACHE_TTL_FUNNEL = 120
_funnel_gap_cache: dict[str, tuple[float, dict]] = {}


def get_funnel_gap_metrics(db: Session) -> dict[str, Any]:
    """Métricas del primer gap del embudo: leads sin identidad ni pago."""
    cache_key = "funnel_gap_metrics"
    current_time = time()
    if cache_key in _funnel_gap_cache:
        cached_time, cached_data = _funnel_gap_cache[cache_key]
        if current_time - cached_time < CACHE_TTL_FUNNEL:
            return cached_data

    mv_claims_exists = db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_matviews
            WHERE schemaname = 'ops' AND matviewname = 'mv_claims_payment_status_cabinet'
        )
    """)).scalar()
    claims_view = "ops.mv_claims_payment_status_cabinet" if mv_claims_exists else "ops.v_claims_payment_status_cabinet"

    total_leads = db.execute(text("SELECT COUNT(*) FROM public.module_ct_cabinet_leads")).scalar() or 0
    leads_with_identity = db.execute(text("""
        SELECT COUNT(*) FROM canon.identity_links
        WHERE source_table = 'module_ct_cabinet_leads'
    """)).scalar() or 0
    leads_with_claims = db.execute(text(f"""
        SELECT COUNT(DISTINCT il.source_pk)
        FROM canon.identity_links il
        INNER JOIN {claims_view} c ON c.person_key = il.person_key
        WHERE il.source_table = 'module_ct_cabinet_leads'
    """)).scalar() or 0

    result = {
        "total_leads": total_leads,
        "leads_with_identity": leads_with_identity,
        "leads_with_claims": leads_with_claims,
        "leads_without_identity": total_leads - leads_with_identity,
        "leads_without_claims": total_leads - leads_with_claims,
        "leads_without_both": total_leads - leads_with_identity,
        "percentages": {
            "with_identity": round((leads_with_identity / total_leads * 100) if total_leads > 0 else 0, 2),
            "with_claims": round((leads_with_claims / total_leads * 100) if total_leads > 0 else 0, 2),
            "without_identity": round(((total_leads - leads_with_identity) / total_leads * 100) if total_leads > 0 else 0, 2),
            "without_claims": round(((total_leads - leads_with_claims) / total_leads * 100) if total_leads > 0 else 0, 2),
            "without_both": round(((total_leads - leads_with_identity) / total_leads * 100) if total_leads > 0 else 0, 2),
        },
    }
    _funnel_gap_cache[cache_key] = (current_time, result)
    return result


def get_kpi_red_recovery_metrics(db: Session) -> KpiRedRecoveryMetricsResponse:
    """Métricas de recovery del KPI rojo."""
    backlog_result = db.execute(text("SELECT COUNT(*) AS count FROM ops.v_cabinet_kpi_red_backlog"))
    current_backlog = backlog_result.scalar() or 0

    metrics_result = db.execute(text("""
        SELECT metric_date, backlog_start, new_backlog_in, matched_out, backlog_end, net_change, top_fail_reason
        FROM ops.v_cabinet_kpi_red_recovery_metrics_daily
        WHERE metric_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY metric_date DESC
    """))
    metrics_rows = metrics_result.fetchall()

    today_metrics = None
    yesterday_metrics = None
    last_7_days = []
    today = date.today()
    yesterday = date.fromordinal(today.toordinal() - 1)

    for row in metrics_rows:
        metric_dict = {
            "metric_date": row.metric_date,
            "backlog_start": row.backlog_start or 0,
            "new_backlog_in": row.new_backlog_in or 0,
            "matched_out": row.matched_out or 0,
            "backlog_end": row.backlog_end or 0,
            "net_change": row.net_change or 0,
            "top_fail_reason": row.top_fail_reason,
        }
        if row.metric_date == today:
            today_metrics = KpiRedRecoveryMetricsDaily(**metric_dict)
        elif row.metric_date == yesterday:
            yesterday_metrics = KpiRedRecoveryMetricsDaily(**metric_dict)
        if row.metric_date >= date.fromordinal(today.toordinal() - 7):
            last_7_days.append(KpiRedRecoveryMetricsDaily(**metric_dict))

    return KpiRedRecoveryMetricsResponse(
        today=today_metrics,
        yesterday=yesterday_metrics,
        last_7_days=last_7_days,
        current_backlog=current_backlog,
    )


def get_claims_audit_summary(db: Session, limit: int = 10) -> dict[str, Any]:
    """Resumen de auditoría de claims: drivers elegibles sin claims generados."""
    summary_result = db.execute(text("""
        SELECT
            COUNT(*) AS total_drivers_elegibles,
            COUNT(*) FILTER (WHERE should_have_claim_m1 = true) AS total_should_have_m1,
            COUNT(*) FILTER (WHERE has_claim_m1 = true) AS total_has_m1,
            COUNT(*) FILTER (WHERE should_have_claim_m1 = true AND has_claim_m1 = false) AS missing_m1,
            COUNT(*) FILTER (WHERE should_have_claim_m5 = true) AS total_should_have_m5,
            COUNT(*) FILTER (WHERE has_claim_m5 = true) AS total_has_m5,
            COUNT(*) FILTER (WHERE should_have_claim_m5 = true AND has_claim_m5 = false) AS missing_m5,
            COUNT(*) FILTER (WHERE should_have_claim_m25 = true) AS total_should_have_m25,
            COUNT(*) FILTER (WHERE has_claim_m25 = true) AS total_has_m25,
            COUNT(*) FILTER (WHERE should_have_claim_m25 = true AND has_claim_m25 = false) AS missing_m25
        FROM ops.v_cabinet_claims_audit_14d
    """))
    summary_row = summary_result.fetchone()
    summary = {
        "total_drivers_elegibles": summary_row.total_drivers_elegibles or 0,
        "m1": {"should_have": summary_row.total_should_have_m1 or 0, "has": summary_row.total_has_m1 or 0, "missing": summary_row.missing_m1 or 0},
        "m5": {"should_have": summary_row.total_should_have_m5 or 0, "has": summary_row.total_has_m5 or 0, "missing": summary_row.missing_m5 or 0},
        "m25": {"should_have": summary_row.total_should_have_m25 or 0, "has": summary_row.total_has_m25 or 0, "missing": summary_row.missing_m25 or 0},
    }

    root_causes_result = db.execute(text("""
        SELECT root_cause, COUNT(*) AS count,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'M1_MISSING') AS m1_missing,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'M5_MISSING') AS m5_missing,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'M25_MISSING') AS m25_missing,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'MULTIPLE_MISSING') AS multiple_missing
        FROM ops.v_cabinet_claims_audit_14d
        WHERE missing_claim_bucket != 'NONE'
        GROUP BY root_cause
        ORDER BY count DESC
    """))
    root_causes = [
        {
            "root_cause": row.root_cause,
            "count": row.count,
            "m1_missing": row.m1_missing or 0,
            "m5_missing": row.m5_missing or 0,
            "m25_missing": row.m25_missing or 0,
            "multiple_missing": row.multiple_missing or 0,
        }
        for row in root_causes_result
    ]

    sample_result = db.execute(
        text("""
            SELECT driver_id, person_key, lead_date, window_end_14d, trips_in_14d,
                should_have_claim_m1, has_claim_m1, should_have_claim_m5, has_claim_m5,
                should_have_claim_m25, has_claim_m25, missing_claim_bucket, root_cause
            FROM ops.v_cabinet_claims_audit_14d
            WHERE missing_claim_bucket != 'NONE'
            ORDER BY lead_date DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )
    sample_cases = []
    for row in sample_result:
        sample_cases.append({
            "driver_id": row.driver_id,
            "person_key": str(row.person_key) if row.person_key else None,
            "lead_date": row.lead_date.isoformat() if row.lead_date else None,
            "window_end_14d": row.window_end_14d.isoformat() if row.window_end_14d else None,
            "trips_in_14d": row.trips_in_14d or 0,
            "should_have_claim_m1": row.should_have_claim_m1,
            "has_claim_m1": row.has_claim_m1,
            "should_have_claim_m5": row.should_have_claim_m5,
            "has_claim_m5": row.has_claim_m5,
            "should_have_claim_m25": row.should_have_claim_m25,
            "has_claim_m25": row.has_claim_m25,
            "missing_claim_bucket": row.missing_claim_bucket,
            "root_cause": row.root_cause,
        })

    return {"summary": summary, "root_causes": root_causes, "sample_cases": sample_cases}
