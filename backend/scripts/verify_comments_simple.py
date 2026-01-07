#!/usr/bin/env python3
"""
Script simple para verificar comentarios SQL (read-only).
"""

import psycopg2
import sys
import os

# Configuración de conexión (usar variables de entorno o valores por defecto)
DB_HOST = os.getenv('DB_HOST', '168.119.226.236')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'yego_integral')
DB_USER = os.getenv('DB_USER', 'yego_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '37>MNA&-35+')

def main():
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cur = conn.cursor()
        
        print("=" * 70)
        print("VERIFICACIÓN DE COMENTARIOS SQL")
        print("=" * 70)
        print()
        
        # Query 1: Comentario de la vista
        print("1) Comentario de la vista ops.v_cabinet_milestones_reconciled:")
        print("-" * 70)
        query1 = """
            SELECT obj_description(
                'ops.v_cabinet_milestones_reconciled'::regclass,
                'pg_class'
            ) AS view_comment;
        """
        cur.execute(query1)
        result1 = cur.fetchone()
        view_comment = result1[0] if result1 else None
        
        if view_comment is None:
            print("✗ NULL - El comentario de la vista NO está presente")
        else:
            print("✓ Comentario encontrado:")
            print(view_comment[:200] + "..." if len(view_comment) > 200 else view_comment)
            print(f"\n(Longitud: {len(view_comment)} caracteres)")
        
        print()
        print()
        
        # Query 2: Comentario de la columna
        print("2) Comentario de la columna reconciliation_status:")
        print("-" * 70)
        query2 = """
            SELECT col_description(
                'ops.v_cabinet_milestones_reconciled'::regclass,
                attnum
            )
            FROM pg_attribute
            WHERE attrelid = 'ops.v_cabinet_milestones_reconciled'::regclass
              AND attname = 'reconciliation_status';
        """
        cur.execute(query2)
        result2 = cur.fetchone()
        column_comment = result2[0] if result2 else None
        
        if column_comment is None:
            print("✗ NULL - El comentario de la columna NO está presente")
        else:
            print("✓ Comentario encontrado:")
            print(column_comment[:200] + "..." if len(column_comment) > 200 else column_comment)
            print(f"\n(Longitud: {len(column_comment)} caracteres)")
        
        print()
        print("=" * 70)
        
        # Verificación final
        if view_comment is not None and column_comment is not None:
            print("✓ Comentarios correctamente persistidos")
            print("=" * 70)
            sys.exit(0)
        else:
            print("✗ ERROR: Algunos comentarios no están presentes")
            if view_comment is None:
                print("  - Falta comentario de la vista")
            if column_comment is None:
                print("  - Falta comentario de la columna")
            print("=" * 70)
            sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ Error ejecutando queries: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()







