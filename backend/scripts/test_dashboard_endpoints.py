"""
Script para verificar los endpoints del dashboard
Ejecutar con: python scripts/test_dashboard_endpoints.py
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
        print("VERIFICACIÓN DE DATOS PARA DASHBOARD")
        print("=" * 80)
        
        # Verificación 1: Totales policy
        print("\n1. Totales Payable Policy:")
        print("-" * 80)
        query1 = text("""
            SELECT 
                COUNT(*) AS n,
                SUM(amount) AS total
            FROM ops.v_scout_liquidation_open_items_payable_policy
        """)
        result1 = session.execute(query1).fetchone()
        print(f"  Count: {result1.n:,}")
        print(f"  Total: {result1.total:,.2f}")
        
        # Verificación 2: Totales unknown
        print("\n2. Totales Blocked (Unknown):")
        print("-" * 80)
        query2 = text("""
            SELECT 
                COUNT(*) AS n,
                SUM(amount) AS total
            FROM ops.v_scout_liquidation_open_items_enriched
            WHERE attribution_confidence = 'unknown'
        """)
        result2 = session.execute(query2).fetchone()
        print(f"  Count: {result2.n:,}")
        print(f"  Total: {result2.total:,.2f}")
        
        # Verificación 3: Yango receivable
        print("\n3. Yango Receivable (últimas 8 semanas):")
        print("-" * 80)
        query3 = text("""
            SELECT 
                pay_week_start_monday,
                pay_iso_year_week,
                total_amount_payable,
                count_payments,
                count_drivers
            FROM ops.v_yango_receivable_payable
            ORDER BY pay_week_start_monday DESC
            LIMIT 8
        """)
        results3 = session.execute(query3).fetchall()
        print("  Semana        | Monto      | Items | Drivers")
        print("  " + "-" * 70)
        for row in results3:
            print(f"  {row.pay_iso_year_week:13s} | {row.total_amount_payable:>10,.2f} | {row.count_payments:5,} | {row.count_drivers:7,}")
        
        print("\n" + "=" * 80)
        print("[OK] VERIFICACIONES COMPLETADAS")
        print("=" * 80)
        print("\nPara probar los endpoints del dashboard:")
        print("1. Iniciar el backend: uvicorn app.main:app --reload")
        print("2. Probar endpoints:")
        print("   - GET http://localhost:8000/api/v1/dashboard/scout/summary")
        print("   - GET http://localhost:8000/api/v1/dashboard/scout/open_items")
        print("   - GET http://localhost:8000/api/v1/dashboard/yango/summary")
        print("   - GET http://localhost:8000/api/v1/dashboard/yango/receivable_items")
        print("3. Abrir frontend: http://localhost:3000/dashboard")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()








