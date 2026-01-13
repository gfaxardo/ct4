"""Script para verificar estado del deployment de orphans cleanup"""
import sys
from pathlib import Path
from sqlalchemy import text
from app.db import SessionLocal

# Agregar directorio padre al path
sys.path.insert(0, str(Path(__file__).parent))

db = SessionLocal()

try:
    print("=" * 60)
    print("VERIFICACION DE ESTADO DEL DEPLOYMENT")
    print("=" * 60)
    
    # 1. Verificar tabla canon.driver_orphan_quarantine
    print("\n1. Verificando tabla canon.driver_orphan_quarantine...")
    result = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'canon' 
        AND table_name = 'driver_orphan_quarantine'
    """))
    table_exists = result.fetchone() is not None
    print(f"   [{'OK' if table_exists else 'ERROR'}] Tabla existe: {table_exists}")
    
    if table_exists:
        # Contar registros
        result = db.execute(text("SELECT COUNT(*) FROM canon.driver_orphan_quarantine"))
        count = result.fetchone()[0]
        print(f"   [INFO] Registros en quarantine: {count}")
    
    # 2. Verificar tipos ENUM
    print("\n2. Verificando tipos ENUM...")
    result = db.execute(text("""
        SELECT typname 
        FROM pg_type 
        WHERE typname IN ('orphan_detected_reason', 'orphan_status')
        ORDER BY typname
    """))
    enums = [row[0] for row in result.fetchall()]
    print(f"   [{'OK' if len(enums) == 2 else 'ERROR'}] ENUMs encontrados: {enums}")
    
    # 3. Verificar vistas requeridas
    print("\n3. Verificando vistas SQL...")
    required_views = [
        'v_driver_orphans',
        'v_cabinet_funnel_status',
        'v_payment_calculation',
        'v_ct4_eligible_drivers'
    ]
    
    result = db.execute(text("""
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = ANY(:views)
        ORDER BY table_name
    """), {"views": required_views})
    
    existing_views = [row[0] for row in result.fetchall()]
    missing_views = set(required_views) - set(existing_views)
    
    print(f"   [{'OK' if len(missing_views) == 0 else 'PENDIENTE'}] Vistas encontradas: {existing_views}")
    if missing_views:
        print(f"   [WARNING] Vistas faltantes: {missing_views}")
    
    # 4. Verificar versión de Alembic
    print("\n4. Verificando versión de Alembic...")
    result = db.execute(text("SELECT version_num FROM alembic_version"))
    row = result.fetchone()
    version = row[0] if row else None
    print(f"   [INFO] Version actual de Alembic: {version}")
    
    # 5. Verificar exclusión de orphans en vistas (si existen)
    if existing_views:
        print("\n5. Verificando exclusion de orphans en vistas...")
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM canon.driver_orphan_quarantine 
            WHERE status = 'quarantined'
        """))
        orphans_count = result.fetchone()[0]
        print(f"   [INFO] Drivers en cuarentena: {orphans_count}")
        
        if 'v_cabinet_funnel_status' in existing_views:
            result = db.execute(text("""
                SELECT COUNT(*) 
                FROM ops.v_cabinet_funnel_status 
                WHERE driver_id IN (
                    SELECT driver_id 
                    FROM canon.driver_orphan_quarantine 
                    WHERE status = 'quarantined'
                )
            """))
            orphans_in_funnel = result.fetchone()[0]
            print(f"   [{'OK' if orphans_in_funnel == 0 else 'ERROR'}] Orphans en v_cabinet_funnel_status: {orphans_in_funnel}")
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Tabla quarantine: {'OK' if table_exists else 'ERROR'}")
    print(f"ENUMs: {'OK' if len(enums) == 2 else 'ERROR'}")
    print(f"Vistas: {len(existing_views)}/{len(required_views)} creadas")
    if missing_views:
        print(f"PENDIENTE: Aplicar vistas faltantes: {missing_views}")
    
finally:
    db.close()

