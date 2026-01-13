"""
Materialized View maintenance service.

Provides functionality to refresh materialized views and track their status.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Lista de MVs críticas que deben mantenerse actualizadas
CRITICAL_MVS = [
    {"schema": "ops", "name": "mv_cabinet_financial_14d", "priority": 1},
    {"schema": "ops", "name": "mv_yango_cabinet_claims_for_collection", "priority": 1},
    {"schema": "ops", "name": "mv_driver_name_index", "priority": 2},
    {"schema": "ops", "name": "mv_yango_payments_ledger_latest_enriched", "priority": 2},
    {"schema": "ops", "name": "mv_yango_payments_ledger_latest", "priority": 2},
    {"schema": "ops", "name": "mv_yango_payments_raw_current", "priority": 3},
]


def refresh_mv(
    db: Session, 
    schema: str, 
    mv_name: str, 
    concurrent: bool = True
) -> Dict:
    """
    Refresh a single materialized view.
    
    Args:
        db: Database session
        schema: Schema name
        mv_name: Materialized view name
        concurrent: Use CONCURRENTLY if possible (requires unique index)
        
    Returns:
        Dict with status, duration, and any error message
    """
    full_name = f"{schema}.{mv_name}"
    start_time = datetime.now(timezone.utc)
    
    try:
        # Verificar que la MV existe
        check = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_matviews 
                WHERE schemaname = :schema AND matviewname = :mv_name
            )
        """), {"schema": schema, "mv_name": mv_name})
        
        if not check.scalar():
            return {
                "mv": full_name,
                "status": "error",
                "error": "MV does not exist",
                "duration_seconds": 0
            }
        
        # Intentar REFRESH CONCURRENTLY primero (más rápido, no bloquea)
        if concurrent:
            try:
                db.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {full_name}"))
                db.commit()
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # Log del refresh
                _log_refresh(db, schema, mv_name, "SUCCESS", duration)
                
                return {
                    "mv": full_name,
                    "status": "success",
                    "method": "concurrent",
                    "duration_seconds": round(duration, 2)
                }
            except Exception as e:
                db.rollback()
                # Si CONCURRENTLY falla (sin índice único), intentar normal
                if "unique index" in str(e).lower() or "concurrently" in str(e).lower():
                    logger.info(f"CONCURRENTLY failed for {full_name}, trying normal refresh")
                else:
                    raise
        
        # REFRESH normal (puede bloquear lecturas)
        db.execute(text(f"REFRESH MATERIALIZED VIEW {full_name}"))
        db.commit()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Log del refresh
        _log_refresh(db, schema, mv_name, "SUCCESS", duration)
        
        return {
            "mv": full_name,
            "status": "success",
            "method": "normal",
            "duration_seconds": round(duration, 2)
        }
        
    except Exception as e:
        db.rollback()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        error_msg = str(e)[:200]
        
        # Log del error
        _log_refresh(db, schema, mv_name, "FAILED", duration, error_msg)
        
        logger.error(f"Failed to refresh {full_name}: {error_msg}")
        return {
            "mv": full_name,
            "status": "error",
            "error": error_msg,
            "duration_seconds": round(duration, 2)
        }


def refresh_all_critical_mvs(db: Session, priority: Optional[int] = None) -> Dict:
    """
    Refresh all critical materialized views.
    
    Args:
        db: Database session
        priority: If set, only refresh MVs with this priority or higher
        
    Returns:
        Dict with summary and individual results
    """
    results = []
    total_duration = 0
    success_count = 0
    error_count = 0
    
    mvs_to_refresh = CRITICAL_MVS
    if priority is not None:
        mvs_to_refresh = [mv for mv in CRITICAL_MVS if mv["priority"] <= priority]
    
    for mv in mvs_to_refresh:
        result = refresh_mv(db, mv["schema"], mv["name"])
        results.append(result)
        total_duration += result.get("duration_seconds", 0)
        
        if result["status"] == "success":
            success_count += 1
        else:
            error_count += 1
    
    return {
        "summary": {
            "total": len(results),
            "success": success_count,
            "errors": error_count,
            "total_duration_seconds": round(total_duration, 2)
        },
        "results": results
    }


def get_mv_status(db: Session) -> List[Dict]:
    """
    Get the current status of all critical MVs.
    
    Returns:
        List of dicts with MV status information
    """
    results = []
    
    for mv in CRITICAL_MVS:
        try:
            # Primero verificar si existe la MV
            exists_check = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = :schema AND matviewname = :mv_name
                )
            """), {"schema": mv["schema"], "mv_name": mv["name"]})
            
            if not exists_check.scalar():
                results.append({
                    "schema": mv["schema"],
                    "name": mv["name"],
                    "priority": mv["priority"],
                    "exists": False
                })
                continue
            
            # Obtener información de la MV
            full_name = f"{mv['schema']}.{mv['name']}"
            info = db.execute(text("""
                SELECT 
                    m.ispopulated,
                    pg_size_pretty(pg_relation_size(format('%I.%I', m.schemaname, m.matviewname)::regclass)) AS size
                FROM pg_matviews m
                WHERE m.schemaname = :schema AND m.matviewname = :mv_name
            """), {"schema": mv["schema"], "mv_name": mv["name"]}).fetchone()
            
            # Obtener último refresh del log (columnas pueden variar según versión de la tabla)
            try:
                log_info = db.execute(text("""
                    SELECT refreshed_at, status, 
                           COALESCE(duration_seconds, duration_ms / 1000.0) as duration_secs
                    FROM ops.mv_refresh_log
                    WHERE schema_name = :schema AND mv_name = :mv_name
                    ORDER BY refreshed_at DESC
                    LIMIT 1
                """), {"schema": mv["schema"], "mv_name": mv["name"]}).fetchone()
            except Exception:
                log_info = None
            
            result_item = {
                "schema": mv["schema"],
                "name": mv["name"],
                "priority": mv["priority"],
                "exists": True,
                "populated": info.ispopulated if info else False,
                "size": info.size if info else "N/A"
            }
            
            if log_info:
                result_item["last_refresh"] = log_info.refreshed_at.isoformat() if log_info.refreshed_at else None
                result_item["last_status"] = log_info.status
                result_item["last_duration_seconds"] = float(log_info.duration_secs) if log_info.duration_secs else None
            
            results.append(result_item)
                
        except Exception as e:
            logger.error(f"Error getting status for {mv['schema']}.{mv['name']}: {e}")
            # Rollback para limpiar transacción fallida
            try:
                db.rollback()
            except Exception:
                pass
            results.append({
                "schema": mv["schema"],
                "name": mv["name"],
                "priority": mv["priority"],
                "exists": False,
                "error": str(e)[:100]
            })
    
    return results


def _log_refresh(
    db: Session, 
    schema: str, 
    mv_name: str, 
    status: str, 
    duration: float,
    error_message: Optional[str] = None
) -> None:
    """Log a refresh attempt to the mv_refresh_log table."""
    try:
        db.execute(text("""
            INSERT INTO ops.mv_refresh_log 
            (schema_name, mv_name, refreshed_at, status, duration_seconds, error_message)
            VALUES (:schema, :mv_name, NOW(), :status, :duration, :error)
        """), {
            "schema": schema,
            "mv_name": mv_name,
            "status": status,
            "duration": duration,
            "error": error_message
        })
        db.commit()
    except Exception as e:
        # Si falla el log, no interrumpir el proceso
        db.rollback()
        logger.warning(f"Failed to log refresh: {e}")
