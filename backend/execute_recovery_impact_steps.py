#!/usr/bin/env python
"""
Script para ejecutar los próximos pasos de Recovery Impact:
1. Ejecutar migración (alembic upgrade head)
2. Crear vistas SQL
3. Verificar que todo funciona
"""
import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db import SessionLocal

def execute_migration():
    """Ejecutar migración usando alembic"""
    print("=" * 80)
    print("PASO 1: Ejecutando migración...")
    print("=" * 80)
    
    # Nota: La migración debe ejecutarse manualmente con: alembic upgrade head
    print("NOTA: La migracion debe ejecutarse manualmente:")
    print("   cd backend")
    print("   alembic upgrade head")
    print()

def create_views():
    """Crear vistas SQL"""
    print("=" * 80)
    print("PASO 2: Creando vistas SQL...")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Vista 1: v_cabinet_lead_identity_effective
        print("Creando vista: ops.v_cabinet_lead_identity_effective...")
        with open('sql/ops/v_cabinet_lead_identity_effective.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        db.execute(text(sql_content))
        db.commit()
        print("[OK] Vista v_cabinet_lead_identity_effective creada exitosamente")
        print()
        
        # Vista 2: v_cabinet_identity_recovery_impact_14d
        print("Creando vista: ops.v_cabinet_identity_recovery_impact_14d...")
        with open('sql/ops/v_cabinet_identity_recovery_impact_14d.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        db.execute(text(sql_content))
        db.commit()
        print("[OK] Vista v_cabinet_identity_recovery_impact_14d creada exitosamente")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error creando vistas: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_views():
    """Verificar que las vistas existen"""
    print("=" * 80)
    print("PASO 3: Verificando vistas...")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Verificar vista 1
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.views 
            WHERE table_schema = 'ops' 
            AND table_name = 'v_cabinet_lead_identity_effective'
        """))
        count = result.scalar()
        if count > 0:
            print("[OK] Vista v_cabinet_lead_identity_effective existe")
        else:
            print("[ERROR] Vista v_cabinet_lead_identity_effective NO existe")
        
        # Verificar vista 2
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.views 
            WHERE table_schema = 'ops' 
            AND table_name = 'v_cabinet_identity_recovery_impact_14d'
        """))
        count = result.scalar()
        if count > 0:
            print("[OK] Vista v_cabinet_identity_recovery_impact_14d existe")
        else:
            print("[ERROR] Vista v_cabinet_identity_recovery_impact_14d NO existe")
        
        # Verificar tabla de auditoría
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'ops' 
            AND table_name = 'cabinet_lead_recovery_audit'
        """))
        count = result.scalar()
        if count > 0:
            print("[OK] Tabla ops.cabinet_lead_recovery_audit existe")
        else:
            print("[ERROR] Tabla ops.cabinet_lead_recovery_audit NO existe")
            print("   Ejecutar: alembic upgrade head")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error verificando vistas: {e}")
        raise
    finally:
        db.close()

def test_views():
    """Probar que las vistas funcionan"""
    print("=" * 80)
    print("PASO 4: Probando vistas...")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Probar vista 1
        result = db.execute(text("SELECT COUNT(*) FROM ops.v_cabinet_lead_identity_effective"))
        count = result.scalar()
        print(f"[OK] Vista v_cabinet_lead_identity_effective: {count} registros")
        
        # Probar vista 2 (solo contar, no traer todos los registros)
        result = db.execute(text("SELECT COUNT(*) FROM ops.v_cabinet_identity_recovery_impact_14d"))
        count = result.scalar()
        print(f"[OK] Vista v_cabinet_identity_recovery_impact_14d: {count} registros")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error probando vistas: {e}")
        raise
    finally:
        db.close()

def main():
    """Ejecutar todos los pasos"""
    print("\n" + "=" * 80)
    print("EJECUCIÓN: Próximos Pasos Recovery Impact")
    print("=" * 80 + "\n")
    
    try:
        # Paso 1: Migración (nota manual)
        execute_migration()
        
        # Paso 2: Crear vistas
        create_views()
        
        # Paso 3: Verificar
        verify_views()
        
        # Paso 4: Probar
        test_views()
        
        print("=" * 80)
        print("[OK] Todos los pasos ejecutados exitosamente")
        print("=" * 80)
        print("\nPróximos pasos:")
        print("1. Ejecutar migración: alembic upgrade head")
        print("2. Probar endpoint: GET /api/v1/yango/cabinet/identity-recovery-impact-14d")
        print("3. (Opcional) Ejecutar job: python -m jobs.cabinet_recovery_impact_job 1000")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la ejecucion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
