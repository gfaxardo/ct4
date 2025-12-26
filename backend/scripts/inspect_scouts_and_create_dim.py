import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("=" * 80)
        print("1. INSPECCIÓN DE SCHEMA: public.module_ct_scouts_list")
        print("=" * 80)
        
        # Obtener schema
        schema_query = text("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                ordinal_position,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = 'module_ct_scouts_list'
            ORDER BY ordinal_position
        """)
        
        result = session.execute(schema_query)
        columns = []
        print("\nColumnas:")
        print("-" * 80)
        for row in result:
            nullable = "NULL" if row.is_nullable == "YES" else "NOT NULL"
            default = f" DEFAULT {row.column_default}" if row.column_default else ""
            print(f"  {row.ordinal_position:3d}. {row.column_name:40s} {row.data_type:30s} {nullable}{default}")
            columns.append({
                "column_name": row.column_name,
                "data_type": row.data_type,
                "is_nullable": row.is_nullable
            })
        
        # Obtener 20 filas
        print("\n" + "=" * 80)
        print("2. PRIMERAS 20 FILAS: public.module_ct_scouts_list")
        print("=" * 80)
        
        rows_query = text("SELECT * FROM public.module_ct_scouts_list LIMIT 20")
        result = session.execute(rows_query)
        
        # Obtener nombres de columnas
        column_names = [col["column_name"] for col in columns]
        
        # Mostrar filas
        print("\n")
        rows = result.fetchall()
        if rows:
            # Imprimir encabezados
            header = " | ".join([f"{name:20s}" for name in column_names])
            print(header)
            print("-" * len(header))
            # Imprimir filas
            for row in rows:
                row_str = " | ".join([f"{str(val):20s}" if val is not None else f"{'NULL':20s}" for val in row])
                print(row_str)
        print(f"\nTotal de filas mostradas: {len(rows)}")
        
        # Verificar si existe columna is_active
        has_is_active = any(col["column_name"] == "is_active" for col in columns)
        print(f"\n¿Existe columna 'is_active'? {has_is_active}")
        
        # Identificar columnas clave
        scout_id_col = None
        name_col = None
        
        for col in columns:
            col_name_lower = col["column_name"].lower()
            if "scout_id" in col_name_lower or col_name_lower == "id":
                scout_id_col = col["column_name"]
            if "name" in col_name_lower:
                name_col = col["column_name"]
        
        print(f"\nColumna identificada para scout_id: {scout_id_col}")
        print(f"Columna identificada para name: {name_col}")
        
        # Crear la vista
        print("\n" + "=" * 80)
        print("3. CREANDO VISTA: ops.v_dim_scouts")
        print("=" * 80)
        
        # Construir la query de la vista
        if not scout_id_col:
            raise ValueError("No se pudo identificar la columna scout_id")
        if not name_col:
            raise ValueError("No se pudo identificar la columna de nombre")
        
        # Normalizar nombre (usar función similar a la que se usa en el proyecto)
        is_active_part = ", is_active" if has_is_active else ""
        view_query = f"""
        CREATE OR REPLACE VIEW ops.v_dim_scouts AS
        SELECT DISTINCT
            {scout_id_col} AS scout_id,
            LOWER(TRIM(REGEXP_REPLACE({name_col}, '[^a-zA-Z0-9\\s]', '', 'g'))) AS scout_name_normalized,
            {name_col} AS raw_name{is_active_part}
        FROM public.module_ct_scouts_list
        WHERE {scout_id_col} IS NOT NULL
        """
        
        print("\nQuery de creación de vista:")
        print("-" * 80)
        print(view_query)
        print("-" * 80)
        
        # Ejecutar creación de vista
        session.execute(text(view_query))
        session.commit()
        print("\n[OK] Vista creada exitosamente")
        
        # Verificaciones
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN DE CONTEOS Y DUPLICADOS")
        print("=" * 80)
        
        # Conteo total en tabla original
        count_original = session.execute(text(f"SELECT COUNT(*) FROM public.module_ct_scouts_list")).scalar()
        print(f"\nTotal de filas en public.module_ct_scouts_list: {count_original:,}")
        
        # Conteo en vista
        count_view = session.execute(text("SELECT COUNT(*) FROM ops.v_dim_scouts")).scalar()
        print(f"Total de filas en ops.v_dim_scouts: {count_view:,}")
        
        # Conteo de scout_id únicos en tabla original
        count_unique_original = session.execute(text(f"SELECT COUNT(DISTINCT {scout_id_col}) FROM public.module_ct_scouts_list WHERE {scout_id_col} IS NOT NULL")).scalar()
        print(f"Total de scout_id únicos en tabla original: {count_unique_original:,}")
        
        # Verificar duplicados de scout_id en tabla original
        duplicates_query = text(f"""
            SELECT 
                {scout_id_col} AS scout_id,
                COUNT(*) AS count
            FROM public.module_ct_scouts_list
            WHERE {scout_id_col} IS NOT NULL
            GROUP BY {scout_id_col}
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        
        duplicates = session.execute(duplicates_query).fetchall()
        print(f"\nDuplicados de scout_id en tabla original (top 10):")
        if duplicates:
            print("-" * 80)
            for dup in duplicates:
                print(f"  scout_id: {dup[0]}, ocurrencias: {dup[1]}")
        else:
            print("  [OK] No hay duplicados de scout_id")
        
        # Verificar duplicados en la vista
        duplicates_view_query = text("""
            SELECT 
                scout_id,
                COUNT(*) AS count
            FROM ops.v_dim_scouts
            GROUP BY scout_id
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        
        duplicates_view = session.execute(duplicates_view_query).fetchall()
        print(f"\nDuplicados de scout_id en vista (top 10):")
        if duplicates_view:
            print("-" * 80)
            for dup in duplicates_view:
                print(f"  scout_id: {dup[0]}, ocurrencias: {dup[1]}")
        else:
            print("  [OK] No hay duplicados de scout_id en la vista")
        
        # Muestra de datos de la vista
        print("\n" + "=" * 80)
        print("5. MUESTRA DE DATOS DE LA VISTA (primeras 10 filas)")
        print("=" * 80)
        
        sample_view_query = text("SELECT * FROM ops.v_dim_scouts ORDER BY scout_id LIMIT 10")
        result_view = session.execute(sample_view_query)
        rows_view = result_view.fetchall()
        
        if rows_view:
            # Obtener nombres de columnas de la vista
            view_columns_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'ops' 
                AND table_name = 'v_dim_scouts'
                ORDER BY ordinal_position
            """)
            view_cols = session.execute(view_columns_query).fetchall()
            view_column_names = [col[0] for col in view_cols]
            
            # Imprimir encabezados
            header = " | ".join([f"{name:30s}" for name in view_column_names])
            print("\n")
            print(header)
            print("-" * len(header))
            # Imprimir filas
            for row in rows_view:
                row_str = " | ".join([f"{str(val):30s}" if val is not None else f"{'NULL':30s}" for val in row])
                print(row_str)
        
        print("\n" + "=" * 80)
        print("[OK] PROCESO COMPLETADO")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()

