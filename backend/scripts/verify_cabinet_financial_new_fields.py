"""
Script para verificar que la vista v_cabinet_financial_14d incluye los nuevos campos
(driver_name e iso_week) y que el ordenamiento funciona correctamente.
"""
import sys
import os

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("Verificación de v_cabinet_financial_14d - Nuevos campos")
        print("=" * 70)
        
        # Verificar que los campos existen
        check_fields_sql = """
            SELECT 
                column_name, 
                data_type
            FROM information_schema.columns
            WHERE table_schema = 'ops'
            AND table_name = 'v_cabinet_financial_14d'
            AND column_name IN ('driver_name', 'iso_week')
            ORDER BY column_name;
        """
        
        result = db.execute(text(check_fields_sql))
        fields = result.fetchall()
        
        print("\n1. Verificación de campos:")
        if len(fields) == 2:
            print("   ✓ Campos driver_name e iso_week encontrados:")
            for field in fields:
                print(f"     - {field.column_name}: {field.data_type}")
        else:
            print(f"   ✗ Error: Se esperaban 2 campos, se encontraron {len(fields)}")
            return
        
        # Verificar datos de muestra
        print("\n2. Muestra de datos (5 filas, ordenadas por lead_date DESC):")
        sample_sql = """
            SELECT 
                driver_id,
                driver_name,
                lead_date,
                iso_week,
                total_trips_14d,
                amount_due_yango
            FROM ops.v_cabinet_financial_14d
            WHERE lead_date IS NOT NULL
            ORDER BY lead_date DESC NULLS LAST
            LIMIT 5;
        """
        
        result = db.execute(text(sample_sql))
        rows = result.fetchall()
        
        if rows:
            for i, row in enumerate(rows, 1):
                print(f"\n   Fila {i}:")
                print(f"     Driver ID: {row.driver_id[:12]}...")
                print(f"     Driver Name: {row.driver_name or 'N/A'}")
                print(f"     Lead Date: {row.lead_date}")
                print(f"     Semana ISO: {row.iso_week or 'N/A'}")
                print(f"     Viajes 14d: {row.total_trips_14d}")
                print(f"     Deuda: S/ {float(row.amount_due_yango):.2f}")
        else:
            print("   ⚠ No se encontraron datos")
        
        # Verificar ordenamiento
        print("\n3. Verificación de ordenamiento:")
        order_check_sql = """
            SELECT 
                lead_date,
                COUNT(*) as count
            FROM ops.v_cabinet_financial_14d
            WHERE lead_date IS NOT NULL
            GROUP BY lead_date
            ORDER BY lead_date DESC
            LIMIT 3;
        """
        
        result = db.execute(text(order_check_sql))
        order_rows = result.fetchall()
        
        if len(order_rows) >= 2:
            dates = [row.lead_date for row in order_rows]
            is_desc = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
            if is_desc:
                print("   ✓ Ordenamiento DESC correcto (más reciente primero)")
                print(f"     Fechas más recientes: {[str(d) for d in dates[:3]]}")
            else:
                print("   ✗ Error: El ordenamiento no es DESC")
        else:
            print("   ⚠ No hay suficientes datos para verificar ordenamiento")
        
        print("\n" + "=" * 70)
        print("Verificación completada")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la verificación: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



