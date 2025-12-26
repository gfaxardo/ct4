"""
Script para verificar los endpoints de liquidación
Ejecutar con: python scripts/test_liquidation_endpoints.py
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
        print("VERIFICACIÓN DE ENDPOINTS DE LIQUIDACIÓN")
        print("=" * 80)
        
        # Verificar que existe un scout con items
        print("\n1. Buscando scout con items pagables:")
        print("-" * 80)
        query1 = text("""
            SELECT 
                acquisition_scout_id,
                acquisition_scout_name,
                COUNT(*) AS items,
                SUM(amount) AS total
            FROM ops.v_scout_liquidation_open_items_payable_policy
            GROUP BY acquisition_scout_id, acquisition_scout_name
            ORDER BY total DESC
            LIMIT 5
        """)
        results1 = session.execute(query1).fetchall()
        if results1:
            print("  Scout ID | Scout Name                    | Items | Total")
            print("  " + "-" * 70)
            for row in results1:
                print(f"  {row.acquisition_scout_id:9d} | {row.acquisition_scout_name or 'N/A':30s} | {row.items:5d} | {row.total:>10,.2f}")
            test_scout_id = results1[0].acquisition_scout_id
            print(f"\n  [OK] Scout {test_scout_id} tiene {results1[0].items} items por {results1[0].total:,.2f} PEN")
        else:
            print("  [WARNING] No hay scouts con items pagables")
            test_scout_id = 1
        
        # Verificar preview query
        print("\n2. Verificando query de preview:")
        print("-" * 80)
        cutoff_date = "2025-12-29"
        query2 = text("""
            SELECT
                COUNT(*) AS preview_items,
                COALESCE(SUM(amount), 0) AS preview_amount
            FROM ops.v_scout_liquidation_open_items_payable_policy
            WHERE acquisition_scout_id = :scout_id
              AND payable_date <= :cutoff_date
        """)
        result2 = session.execute(query2, {"scout_id": test_scout_id, "cutoff_date": cutoff_date}).fetchone()
        print(f"  Scout ID: {test_scout_id}")
        print(f"  Cutoff Date: {cutoff_date}")
        print(f"  Preview Items: {result2.preview_items}")
        print(f"  Preview Amount: {result2.preview_amount:,.2f}")
        
        # Verificar estado antes
        print("\n3. Estado antes de marcar pagado:")
        print("-" * 80)
        query3_before = text("""
            SELECT COUNT(*), SUM(amount)
            FROM ops.v_scout_liquidation_open_items_payable_policy
            WHERE acquisition_scout_id = :scout_id
        """)
        result3_before = session.execute(query3_before, {"scout_id": test_scout_id}).fetchone()
        print(f"  Open Items: {result3_before[0]} items, {result3_before[1] or 0:,.2f} PEN")
        
        query4_before = text("""
            SELECT COUNT(*), SUM(amount)
            FROM ops.scout_liquidation_ledger
            WHERE scout_id = :scout_id
        """)
        result4_before = session.execute(query4_before, {"scout_id": test_scout_id}).fetchone()
        print(f"  Ledger Items: {result4_before[0]} items, {result4_before[1] or 0:,.2f} PEN")
        
        print("\n" + "=" * 80)
        print("INSTRUCCIONES PARA PROBAR ENDPOINTS")
        print("=" * 80)
        print("\n1. Configurar ADMIN_TOKEN en backend/.env:")
        print("   ADMIN_TOKEN=tu_token_secreto_aqui")
        print("\n2. Configurar token en localStorage del navegador:")
        print("   localStorage.setItem('admin_token', 'tu_token_secreto_aqui')")
        print("\n3. Probar preview endpoint:")
        print(f"   curl \"http://localhost:8000/api/v1/liquidation/scout/preview?scout_id={test_scout_id}&cutoff_date={cutoff_date}\"")
        print("\n4. Probar mark_paid endpoint:")
        print(f"   curl -X POST \"http://localhost:8000/api/v1/liquidation/scout/mark_paid\" \\")
        print(f"     -H \"Content-Type: application/json\" \\")
        print(f"     -H \"X-Admin-Token: tu_token_secreto_aqui\" \\")
        print(f"     -d '{{\"scout_id\":{test_scout_id},\"cutoff_date\":\"{cutoff_date}\",\"paid_by\":\"finanzas\",\"payment_ref\":\"TEST-TRX-001\",\"notes\":\"pago semanal\"}}'")
        print("\n5. Verificar cambios:")
        print(f"   SELECT COUNT(*), SUM(amount) FROM ops.v_scout_liquidation_open_items_payable_policy WHERE acquisition_scout_id={test_scout_id};")
        print(f"   SELECT COUNT(*), SUM(amount) FROM ops.scout_liquidation_ledger WHERE scout_id={test_scout_id};")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()


