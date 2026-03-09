"""
Script para crear el constraint único en external_id para module_ct_cabinet_leads
"""
import sys
import os
from pathlib import Path

# Agregar el directorio backend al path para importar módulos
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    print("🔧 Creando constraint único en external_id para module_ct_cabinet_leads...")
    
    # Crear engine
    engine = create_engine(
        settings.database_url,
        connect_args={
            "connect_timeout": 10,
        }
    )
    
    try:
        with engine.connect() as conn:
            # Verificar si hay duplicados
            print("\n1️⃣ Verificando duplicados en external_id...")
            check_duplicates = conn.execute(text("""
                SELECT 
                    external_id,
                    COUNT(*) as count
                FROM public.module_ct_cabinet_leads
                WHERE external_id IS NOT NULL
                GROUP BY external_id
                HAVING COUNT(*) > 1
            """))
            duplicates = check_duplicates.fetchall()
            
            if duplicates:
                print(f"⚠️  ADVERTENCIA: Se encontraron {len(duplicates)} external_ids duplicados:")
                for dup in duplicates[:10]:  # Mostrar solo los primeros 10
                    print(f"   - {dup[0]}: {dup[1]} ocurrencias")
                if len(duplicates) > 10:
                    print(f"   ... y {len(duplicates) - 10} más")
                print("\n❌ No se puede crear el constraint único con duplicados.")
                print("   Por favor, elimina los duplicados primero.")
                return False
            else:
                print("✅ No hay duplicados. Procediendo...")
            
            # Verificar si el constraint ya existe
            print("\n2️⃣ Verificando si el constraint ya existe...")
            check_constraint = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_constraint c
                    JOIN pg_class t ON t.oid = c.conrelid
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    WHERE n.nspname = 'public'
                      AND t.relname = 'module_ct_cabinet_leads'
                      AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
                      AND c.contype = 'u'
                )
            """))
            constraint_exists = check_constraint.scalar()
            
            if constraint_exists:
                print("✅ El constraint ya existe. No es necesario crearlo.")
                return True
            
            # Eliminar constraint existente si hay uno con otro nombre (opcional)
            print("\n3️⃣ Creando constraint único...")
            conn.execute(text("""
                ALTER TABLE public.module_ct_cabinet_leads
                ADD CONSTRAINT uq_module_ct_cabinet_leads_external_id
                UNIQUE (external_id)
            """))
            conn.commit()
            
            # Verificar que se creó correctamente
            verify = conn.execute(text("""
                SELECT 
                    c.conname as constraint_name,
                    t.relname as table_name,
                    n.nspname as schema_name
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public'
                  AND t.relname = 'module_ct_cabinet_leads'
                  AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
                  AND c.contype = 'u'
            """))
            result = verify.fetchone()
            
            if result:
                print(f"✅ Constraint creado exitosamente:")
                print(f"   - Nombre: {result[0]}")
                print(f"   - Tabla: {result[1]}")
                print(f"   - Schema: {result[2]}")
                return True
            else:
                print("❌ Error: El constraint no se creó correctamente.")
                return False
                
    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            print("✅ El constraint ya existe (ignorando error).")
            return True
        elif "violates unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
            print(f"❌ Error: Hay duplicados en la tabla que impiden crear el constraint.")
            print(f"   Detalle: {error_msg}")
            return False
        else:
            print(f"❌ Error creando constraint: {e}")
            return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

