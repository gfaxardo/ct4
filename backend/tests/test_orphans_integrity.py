"""
Tests de Integridad: Drivers Huérfanos (Orphans)
===============================================

Verifica que NO existen drivers operativos sin leads asociados (excepto en cuarentena).
"""

import pytest
from sqlalchemy import text
from app.db import SessionLocal


@pytest.fixture
def db():
    """Fixture para crear una sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_no_drivers_without_leads_outside_quarantine(db):
    """
    Verifica que NO existen drivers sin leads fuera de cuarentena.
    
    CRITERIO DE ACEPTACIÓN:
    - drivers_without_leads operativos = 0 (excepto quarantined)
    """
    query = text("""
        SELECT COUNT(*) as violation_count
        FROM canon.identity_links il
        WHERE il.source_table = 'drivers'
        AND il.person_key NOT IN (
            SELECT DISTINCT person_key
            FROM canon.identity_links
            WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
        )
        AND il.source_pk NOT IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        )
    """)
    
    result = db.execute(query)
    row = result.fetchone()
    violation_count = row.violation_count if row else 0
    
    assert violation_count == 0, (
        f"Se encontraron {violation_count} drivers sin leads fuera de cuarentena. "
        "Todos los drivers sin leads deben estar en cuarentena (status='quarantined')."
    )


def test_funnel_excludes_quarantined_drivers(db):
    """
    Verifica que la vista de funnel excluye drivers en cuarentena.
    
    CRITERIO DE ACEPTACIÓN:
    - ops.v_cabinet_funnel_status NO debe incluir drivers en cuarentena
    """
    query = text("""
        SELECT COUNT(*) as violation_count
        FROM ops.v_cabinet_funnel_status vfs
        WHERE vfs.driver_id IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        )
    """)
    
    result = db.execute(query)
    row = result.fetchone()
    violation_count = row.violation_count if row else 0
    
    assert violation_count == 0, (
        f"Se encontraron {violation_count} drivers en cuarentena en la vista de funnel. "
        "La vista ops.v_cabinet_funnel_status debe excluir automáticamente drivers en cuarentena."
    )


def test_quarantine_table_audit_completeness(db):
    """
    Verifica que todos los drivers sin leads tienen registro en quarantine.
    
    CRITERIO DE ACEPTACIÓN:
    - Todos los drivers sin leads deben tener registro en driver_orphan_quarantine
    """
    query = text("""
        SELECT COUNT(*) as missing_records
        FROM canon.identity_links il
        WHERE il.source_table = 'drivers'
        AND il.person_key NOT IN (
            SELECT DISTINCT person_key
            FROM canon.identity_links
            WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
        )
        AND il.source_pk NOT IN (
            SELECT driver_id FROM canon.driver_orphan_quarantine
        )
    """)
    
    result = db.execute(query)
    row = result.fetchone()
    missing_records = row.missing_records if row else 0
    
    assert missing_records == 0, (
        f"Se encontraron {missing_records} drivers sin leads que NO tienen registro en quarantine. "
        "Todos los drivers sin leads deben tener un registro en canon.driver_orphan_quarantine."
    )


def test_quarantine_status_validity(db):
    """
    Verifica que todos los registros en quarantine tienen status válido.
    
    CRITERIO DE ACEPTACIÓN:
    - Todos los registros en quarantine deben tener status válido
    """
    query = text("""
        SELECT COUNT(*) as invalid_status
        FROM canon.driver_orphan_quarantine q
        WHERE q.status NOT IN ('quarantined', 'resolved_relinked', 'resolved_created_lead', 'purged')
    """)
    
    result = db.execute(query)
    row = result.fetchone()
    invalid_status = row.invalid_status if row else 0
    
    assert invalid_status == 0, (
        f"Se encontraron {invalid_status} registros en quarantine con status inválido. "
        "Todos los registros deben tener status: quarantined, resolved_relinked, resolved_created_lead, o purged."
    )


def test_resolved_orphans_have_resolution_notes(db):
    """
    Verifica que los orphans resueltos tienen notas de resolución.
    
    CRITERIO DE ACEPTACIÓN:
    - Los orphans resueltos deben tener resolution_notes y resolved_at
    """
    query = text("""
        SELECT COUNT(*) as missing_resolution_info
        FROM canon.driver_orphan_quarantine q
        WHERE q.status IN ('resolved_relinked', 'resolved_created_lead')
        AND (q.resolution_notes IS NULL OR q.resolved_at IS NULL)
    """)
    
    result = db.execute(query)
    row = result.fetchone()
    missing_resolution_info = row.missing_resolution_info if row else 0
    
    assert missing_resolution_info == 0, (
        f"Se encontraron {missing_resolution_info} orphans resueltos sin información de resolución. "
        "Todos los orphans resueltos deben tener resolution_notes y resolved_at."
    )



