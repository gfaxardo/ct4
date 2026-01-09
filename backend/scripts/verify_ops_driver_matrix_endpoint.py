"""
Script para verificar el endpoint /api/v1/ops/payments/driver-matrix
Ejecutar con: python scripts/verify_ops_driver_matrix_endpoint.py
"""
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
        print("VERIFICACIÓN: ops.v_payments_driver_matrix_cabinet")
        print("=" * 80)
        
        # Verificación 1: Vista existe
        print("\n1. Verificar que la vista existe:")
        print("-" * 80)
        query1 = text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views 
                WHERE table_schema = 'ops' 
                AND table_name = 'v_payments_driver_matrix_cabinet'
            ) AS view_exists
        """)
        result1 = session.execute(query1).fetchone()
        if result1.view_exists:
            print("  ✅ Vista existe")
        else:
            print("  ❌ Vista NO existe")
            return
        
        # Verificación 2: COUNT total
        print("\n2. COUNT total de drivers:")
        print("-" * 80)
        query2 = text("SELECT COUNT(*) AS total FROM ops.v_payments_driver_matrix_cabinet")
        result2 = session.execute(query2).fetchone()
        print(f"  Total drivers: {result2.total:,}")
        
        # Verificación 3: Sample de datos
        print("\n3. Sample de 5 filas (primeras columnas):")
        print("-" * 80)
        query3 = text("""
            SELECT 
                driver_id,
                driver_name,
                week_start,
                origin_tag,
                m1_achieved_flag,
                m5_achieved_flag,
                m25_achieved_flag
            FROM ops.v_payments_driver_matrix_cabinet
            LIMIT 5
        """)
        result3 = session.execute(query3).fetchall()
        for i, row in enumerate(result3, 1):
            print(f"  {i}. driver_id={row.driver_id}, name={row.driver_name}, week={row.week_start}, origin={row.origin_tag}")
            print(f"     M1={row.m1_achieved_flag}, M5={row.m5_achieved_flag}, M25={row.m25_achieved_flag}")
        
        # Verificación 4: Filtro only_pending (simular lógica del endpoint)
        print("\n4. Verificar filtro only_pending:")
        print("-" * 80)
        query4 = text("""
            SELECT COUNT(*) AS total_pending
            FROM ops.v_payments_driver_matrix_cabinet
            WHERE (
                (m1_achieved_flag = true AND COALESCE(m1_yango_payment_status, '') != 'PAID')
                OR (m5_achieved_flag = true AND COALESCE(m5_yango_payment_status, '') != 'PAID')
                OR (m25_achieved_flag = true AND COALESCE(m25_yango_payment_status, '') != 'PAID')
            )
        """)
        result4 = session.execute(query4).fetchone()
        print(f"  Drivers con al menos 1 milestone pendiente: {result4.total_pending:,}")
        
        # Verificación 5: Filtro origin_tag
        print("\n5. Verificar filtro origin_tag:")
        print("-" * 80)
        query5 = text("""
            SELECT 
                origin_tag,
                COUNT(*) AS count
            FROM ops.v_payments_driver_matrix_cabinet
            WHERE origin_tag IS NOT NULL
            GROUP BY origin_tag
            ORDER BY count DESC
        """)
        result5 = session.execute(query5).fetchall()
        for row in result5:
            print(f"  {row.origin_tag}: {row.count:,}")
        
        # Verificación 6: Ordenamiento (week_start_desc)
        print("\n6. Verificar ordenamiento week_start_desc:")
        print("-" * 80)
        query6 = text("""
            SELECT 
                week_start,
                COUNT(*) AS count
            FROM ops.v_payments_driver_matrix_cabinet
            WHERE week_start IS NOT NULL
            GROUP BY week_start
            ORDER BY week_start DESC
            LIMIT 5
        """)
        result6 = session.execute(query6).fetchall()
        print("  Top 5 semanas (más recientes primero):")
        for row in result6:
            print(f"    {row.week_start}: {row.count:,} drivers")
        
        print("\n" + "=" * 80)
        print("✅ Verificación completada")
        print("=" * 80)
        print("\nPara probar el endpoint API, ejecutar:")
        print("  curl -X GET 'http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=10&offset=0'")
        print("\nO con filtros:")
        print("  curl -X GET 'http://localhost:8000/api/v1/ops/payments/driver-matrix?only_pending=true&limit=50&offset=0'")
        
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()


