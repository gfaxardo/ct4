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
        print("1. CREANDO VISTAS ENRIQUECIDAS DE LIQUIDACIÓN")
        print("=" * 80)
        
        # Leer y ejecutar el SQL
        sql_file = Path(__file__).parent.parent / "sql" / "ops" / "v_liquidation_enriched.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Separar statements
        statements = []
        current_statement = []
        for line in sql_content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
            current_statement.append(line)
            if stripped.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    session.execute(text(statement))
                    session.commit()
                    print(f"  [OK] Statement {i} ejecutado")
                except Exception as e:
                    print(f"  [ERROR] Error en statement {i}: {e}")
                    print(f"  Statement: {statement[:300]}...")
                    raise
        
        print("\n[OK] Todas las vistas creadas exitosamente")
        
        # Verificaciones
        print("\n" + "=" * 80)
        print("2. VERIFICACIÓN A: Conteo por confidence en open_enriched")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT attribution_confidence, COUNT(*) n, SUM(amount) total")
        print("FROM ops.v_scout_liquidation_open_items_enriched")
        print("GROUP BY 1")
        print("ORDER BY 2 DESC;")
        print("\nResultado:")
        print("-" * 80)
        
        query_a = text("""
            SELECT 
                attribution_confidence, 
                COUNT(*) AS n, 
                SUM(amount) AS total
            FROM ops.v_scout_liquidation_open_items_enriched
            GROUP BY attribution_confidence
            ORDER BY COUNT(*) DESC
        """)
        
        result_a = session.execute(query_a)
        print("  attribution_confidence | count      | total")
        print("  " + "-" * 70)
        for row in result_a:
            total_str = f"{row.total:,.2f}" if row.total else "0.00"
            print(f"  {row.attribution_confidence:22s} | {row.n:10,} | {total_str:>15s}")
        
        print("\n" + "=" * 80)
        print("3. VERIFICACIÓN B: Conteo policy (high+medium)")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT COUNT(*) n, SUM(amount) total")
        print("FROM ops.v_scout_liquidation_open_items_payable_policy;")
        print("\nResultado:")
        print("-" * 80)
        
        query_b = text("""
            SELECT 
                COUNT(*) AS n, 
                SUM(amount) AS total
            FROM ops.v_scout_liquidation_open_items_payable_policy
        """)
        
        result_b = session.execute(query_b)
        row_b = result_b.fetchone()
        if row_b:
            total_str = f"{row_b.total:,.2f}" if row_b.total else "0.00"
            print(f"  Count: {row_b.n:,}")
            print(f"  Total: {total_str}")
        
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN C: Cabinet con scout asignado")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT COUNT(*) n")
        print("FROM ops.v_scout_liquidation_open_items_enriched")
        print("WHERE lead_origin='cabinet' AND acquisition_scout_id IS NOT NULL;")
        print("\nResultado:")
        print("-" * 80)
        
        query_c = text("""
            SELECT COUNT(*) AS n
            FROM ops.v_scout_liquidation_open_items_enriched
            WHERE lead_origin = 'cabinet' 
            AND acquisition_scout_id IS NOT NULL
        """)
        
        result_c = session.execute(query_c)
        count_c = result_c.scalar()
        print(f"  Total: {count_c:,}")
        
        print("\n" + "=" * 80)
        print("5. VERIFICACIÓN D: 20 items recientes")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT *")
        print("FROM ops.v_scout_liquidation_open_items_enriched")
        print("ORDER BY payable_date DESC")
        print("LIMIT 20;")
        print("\nResultado:")
        print("-" * 80)
        
        query_d = text("""
            SELECT 
                payment_item_key,
                person_key,
                lead_origin,
                scout_id,
                acquisition_scout_id,
                acquisition_scout_name,
                attribution_confidence,
                attribution_rule,
                milestone_type,
                milestone_value,
                payable_date,
                amount,
                currency
            FROM ops.v_scout_liquidation_open_items_enriched
            ORDER BY payable_date DESC
            LIMIT 20
        """)
        
        result_d = session.execute(query_d)
        rows_d = result_d.fetchall()
        
        if rows_d:
            print("\n  payment_item_key                    | person_key                         | lead_origin | scout_id | attr_scout_id | attr_scout_name              | confidence | rule              | amount")
            print("  " + "-" * 180)
            for row in rows_d:
                scout_id_str = str(row.scout_id) if row.scout_id else "NULL"
                attr_scout_id_str = str(row.acquisition_scout_id) if row.acquisition_scout_id else "NULL"
                attr_scout_name_str = (row.acquisition_scout_name or "NULL")[:30]
                amount_str = f"{row.amount:,.2f}" if row.amount else "0.00"
                print(f"  {row.payment_item_key:35s} | {str(row.person_key):36s} | {row.lead_origin:11s} | {scout_id_str:8s} | {attr_scout_id_str:13s} | {attr_scout_name_str:30s} | {row.attribution_confidence:10s} | {row.attribution_rule:18s} | {amount_str:>10s}")
        else:
            print("\n  No hay items")
        
        print("\n" + "=" * 80)
        print("[OK] TODAS LAS VERIFICACIONES COMPLETADAS")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()


























