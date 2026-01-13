"""Script para ejecutar verificaciones post-deploy de orphans cleanup"""
import sys
from pathlib import Path
from sqlalchemy import text
from app.db import SessionLocal

sys.path.insert(0, str(Path(__file__).parent))

db = SessionLocal()

try:
    print("=" * 80)
    print("VERIFICACION POST-DEPLOY: Sistema de Eliminacion de Orphans")
    print("=" * 80)
    
    checks = []
    
    # 1. Drivers sin lead operativos = 0
    print("\n1. Verificando drivers sin lead operativos...")
    result = db.execute(text("""
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
    """))
    violation_count = result.fetchone()[0]
    checks.append({
        "name": "Drivers sin lead operativos",
        "violation_count": violation_count,
        "status": "PASS" if violation_count == 0 else "FAIL"
    })
    print(f"   [{'OK' if violation_count == 0 else 'ERROR'}] Violaciones: {violation_count}")
    
    # 2. Vistas excluyen orphans
    print("\n2. Verificando exclusion de orphans en vistas...")
    
    # 2.1. Funnel
    result = db.execute(text("""
        SELECT COUNT(*) as orphans_in_funnel
        FROM ops.v_cabinet_funnel_status vfs
        WHERE vfs.driver_id IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        )
    """))
    orphans_in_funnel = result.fetchone()[0]
    checks.append({
        "name": "Funnel excluye orphans",
        "violation_count": orphans_in_funnel,
        "status": "PASS" if orphans_in_funnel == 0 else "FAIL"
    })
    print(f"   [{'OK' if orphans_in_funnel == 0 else 'ERROR'}] Orphans en funnel: {orphans_in_funnel}")
    
    # 2.2. Pagos
    result = db.execute(text("""
        SELECT COUNT(*) as orphans_in_payments
        FROM ops.v_payment_calculation vpc
        WHERE vpc.driver_id IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        )
    """))
    orphans_in_payments = result.fetchone()[0]
    checks.append({
        "name": "Pagos excluyen orphans",
        "violation_count": orphans_in_payments,
        "status": "PASS" if orphans_in_payments == 0 else "FAIL"
    })
    print(f"   [{'OK' if orphans_in_payments == 0 else 'ERROR'}] Orphans en pagos: {orphans_in_payments}")
    
    # 2.3. Elegibilidad
    result = db.execute(text("""
        SELECT COUNT(*) as orphans_in_eligible
        FROM ops.v_ct4_eligible_drivers ved
        WHERE ved.driver_id IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        )
    """))
    orphans_in_eligible = result.fetchone()[0]
    checks.append({
        "name": "Elegibilidad excluye orphans",
        "violation_count": orphans_in_eligible,
        "status": "PASS" if orphans_in_eligible == 0 else "FAIL"
    })
    print(f"   [{'OK' if orphans_in_eligible == 0 else 'ERROR'}] Orphans en elegibilidad: {orphans_in_eligible}")
    
    # 3. Auditoria completa
    print("\n3. Verificando auditoria completa...")
    result = db.execute(text("""
        SELECT COUNT(*) as missing_quarantine_records
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
    """))
    missing_quarantine = result.fetchone()[0]
    checks.append({
        "name": "Auditoria completa (todo driver sin lead tiene registro en quarantine)",
        "violation_count": missing_quarantine,
        "status": "PASS" if missing_quarantine == 0 else "FAIL"
    })
    print(f"   [{'OK' if missing_quarantine == 0 else 'ERROR'}] Registros faltantes en quarantine: {missing_quarantine}")
    
    # 4. Estadisticas de quarantine
    print("\n4. Estadisticas de quarantine...")
    result = db.execute(text("""
        SELECT 
            status,
            COUNT(*) as count
        FROM canon.driver_orphan_quarantine
        GROUP BY status
        ORDER BY status
    """))
    stats = {row[0]: row[1] for row in result.fetchall()}
    total_quarantine = sum(stats.values())
    print(f"   [INFO] Total en quarantine: {total_quarantine}")
    for status, count in stats.items():
        print(f"   [INFO]   - {status}: {count}")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE VERIFICACIONES")
    print("=" * 80)
    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    print(f"Verificaciones PASADAS: {passed}/{len(checks)}")
    print(f"Verificaciones FALLIDAS: {failed}/{len(checks)}")
    
    if failed > 0:
        print("\nVerificaciones FALLIDAS:")
        for check in checks:
            if check["status"] == "FAIL":
                print(f"  - {check['name']}: {check['violation_count']} violaciones")
    else:
        print("\n[TODAS LAS VERIFICACIONES PASARON] El deployment fue exitoso!")
    
    print("\n" + "=" * 80)
    
finally:
    db.close()



