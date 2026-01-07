"""
Script simple para crear el constraint único en external_id
Usa psycopg2 directamente sin depender de módulos de la app
"""
import psycopg2
import sys

# Configuración de base de datos
DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"

def main():
    print("Creando constraint unico en external_id para module_ct_cabinet_leads...")
    
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()
        
        try:
            # 1. Verificar si hay duplicados
            print("\n1. Verificando duplicados en external_id...")
            cur.execute("""
                SELECT 
                    external_id,
                    COUNT(*) as count
                FROM public.module_ct_cabinet_leads
                WHERE external_id IS NOT NULL
                GROUP BY external_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()
            
            if duplicates:
                print(f"ADVERTENCIA: Se encontraron {len(duplicates)} external_ids duplicados:")
                for dup in duplicates[:10]:
                    print(f"   - {dup[0]}: {dup[1]} ocurrencias")
                if len(duplicates) > 10:
                    print(f"   ... y {len(duplicates) - 10} mas")
                print("\nERROR: No se puede crear el constraint unico con duplicados.")
                return False
            else:
                print("OK: No hay duplicados. Procediendo...")
            
            # 2. Verificar si el constraint ya existe
            print("\n2. Verificando si el constraint ya existe...")
            cur.execute("""
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
            """)
            constraint_exists = cur.fetchone()[0]
            
            if constraint_exists:
                print("OK: El constraint ya existe. No es necesario crearlo.")
                return True
            
            # 3. Crear constraint único
            print("\n3. Creando constraint unico...")
            cur.execute("""
                ALTER TABLE public.module_ct_cabinet_leads
                ADD CONSTRAINT uq_module_ct_cabinet_leads_external_id
                UNIQUE (external_id)
            """)
            conn.commit()
            
            # 4. Verificar que se creó correctamente
            print("\n4. Verificando que se creo correctamente...")
            cur.execute("""
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
            """)
            result = cur.fetchone()
            
            if result:
                print(f"OK: Constraint creado exitosamente:")
                print(f"   - Nombre: {result[0]}")
                print(f"   - Tabla: {result[1]}")
                print(f"   - Schema: {result[2]}")
                return True
            else:
                print("ERROR: El constraint no se creo correctamente.")
                return False
                
        except psycopg2.errors.UniqueViolation as e:
            conn.rollback()
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                print("OK: El constraint ya existe (ignorando error).")
                return True
            else:
                print(f"ERROR: Hay duplicados en la tabla que impiden crear el constraint.")
                print(f"   Detalle: {error_msg}")
                return False
        except psycopg2.errors.DuplicateTable as e:
            conn.rollback()
            print("OK: El constraint ya existe (ignorando error).")
            return True
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print("OK: El constraint ya existe (ignorando error).")
                return True
            else:
                print(f"ERROR creando constraint: {e}")
                return False
        finally:
            cur.close()
            
    except psycopg2.OperationalError as e:
        print(f"ERROR de conexion a la base de datos: {e}")
        return False
    except Exception as e:
        print(f"ERROR inesperado: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

