#!/usr/bin/env python3
"""
Script para ejecutar comentarios SQL sobre PAID_WITHOUT_ACHIEVEMENT.
Solo ejecuta COMMENT ON (read-only, no modifica lógica).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.db import SessionLocal, engine


def verify_view_type(session):
    """Verifica que ops.v_cabinet_milestones_reconciled sea VIEW."""
    query = text("""
        SELECT 
            CASE c.relkind
                WHEN 'v' THEN 'VIEW'
                WHEN 'm' THEN 'MATERIALIZED VIEW'
                WHEN 'r' THEN 'TABLE'
                ELSE 'OTHER'
            END AS object_type
        FROM pg_class c
        INNER JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'ops'
            AND c.relname = 'v_cabinet_milestones_reconciled';
    """)
    
    result = session.execute(query).fetchone()
    
    if result is None:
        raise Exception("El objeto ops.v_cabinet_milestones_reconciled no existe")
    
    object_type = result[0]
    
    if object_type != 'VIEW':
        raise Exception(f"El objeto ops.v_cabinet_milestones_reconciled es {object_type} (no es VIEW). Deteniendo ejecución.")
    
    print(f"✓ Verificación OK: ops.v_cabinet_milestones_reconciled es {object_type}")
    return True


def execute_comment_on_view(session):
    """Ejecuta COMMENT ON VIEW."""
    comment = """Vista de reconciliación que hace JOIN explícito entre ACHIEVED (operativo) y PAID (pagos Yango). Expone reconciliation_status que categoriza cada milestone en 4 estados mutuamente excluyentes: OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE. Grano: (driver_id, milestone_value). IMPORTANTE: PAID_WITHOUT_ACHIEVEMENT es válido y esperado (no es un bug). Indica que Yango pagó según sus criterios upstream, sin evidencia suficiente en nuestro sistema operativo. Subtipos: UPSTREAM_OVERPAYMENT (~79%) e INSUFFICIENT_TRIPS_CONFIRMED (~21%). Principio: el pasado no se corrige, se explica. NO recalcular milestones históricos ni modificar pagos pasados. Ver: docs/policies/ct4_reconciliation_status_policy.md y docs/runbooks/paid_without_achievement_expected_behavior.md"""
    
    # Escapar comillas simples duplicándolas para SQL
    comment_escaped = comment.replace("'", "''")
    query = text(f"COMMENT ON VIEW ops.v_cabinet_milestones_reconciled IS '{comment_escaped}'")
    session.execute(query)
    session.commit()
    print("✓ COMMENT ON VIEW ejecutado correctamente")


def execute_comment_on_column(session):
    """Ejecuta COMMENT ON COLUMN."""
    comment = """Estado de reconciliación (mutuamente excluyente): OK (alcanzado y pagado), ACHIEVED_NOT_PAID (alcanzado pero no pagado), PAID_WITHOUT_ACHIEVEMENT (pagado pero no alcanzado), NOT_APPLICABLE (ni alcanzado ni pagado - no debería aparecer en producción). IMPORTANTE: PAID_WITHOUT_ACHIEVEMENT es válido y esperado (no es un bug). Yango pagó según sus criterios upstream, sin evidencia suficiente en summary_daily. Subtipos: UPSTREAM_OVERPAYMENT (~79%, lógica propia de Yango) e INSUFFICIENT_TRIPS_CONFIRMED (~21%, trips insuficientes en ventana). Principio: el pasado no se corrige, se explica. NO recalcular milestones históricos, NO modificar reglas pasadas, NO reabrir pagos ya ejecutados. Queries de diagnóstico: fase2_clasificacion_masiva_paid_without_achievement.sql, fase2_diagnostic_paid_without_achievement.sql. Ver: docs/policies/ct4_reconciliation_status_policy.md y docs/runbooks/paid_without_achievement_expected_behavior.md"""
    
    # Escapar comillas simples duplicándolas para SQL
    comment_escaped = comment.replace("'", "''")
    query = text(f"COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.reconciliation_status IS '{comment_escaped}'")
    session.execute(query)
    session.commit()
    print("✓ COMMENT ON COLUMN ejecutado correctamente")


def main():
    """Función principal."""
    db = SessionLocal()
    
    try:
        print("Ejecutando comentarios SQL sobre PAID_WITHOUT_ACHIEVEMENT...")
        print("")
        
        # Paso 1: Verificar tipo de objeto
        verify_view_type(db)
        
        # Paso 2: Ejecutar COMMENT ON VIEW
        execute_comment_on_view(db)
        
        # Paso 3: Ejecutar COMMENT ON COLUMN
        execute_comment_on_column(db)
        
        print("")
        print("=" * 70)
        print("✓ COMMENT ON ejecutado correctamente sobre VIEW")
        print("=" * 70)
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

