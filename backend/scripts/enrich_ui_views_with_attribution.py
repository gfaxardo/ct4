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
        print("1. APLICANDO MODIFICACIONES A VISTAS UI")
        print("=" * 80)
        
        # Leer y ejecutar v_payments_reports_ui.sql
        sql_file1 = Path(__file__).parent.parent / "sql" / "ops" / "v_payments_reports_ui.sql"
        with open(sql_file1, 'r', encoding='utf-8') as f:
            sql_content1 = f.read()
        
        # Separar statements
        statements1 = []
        current_statement = []
        for line in sql_content1.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
            current_statement.append(line)
            if stripped.endswith(';'):
                statements1.append('\n'.join(current_statement))
                current_statement = []
        
        if current_statement:
            statements1.append('\n'.join(current_statement))
        
        for i, statement in enumerate(statements1, 1):
            if statement.strip() and 'CREATE OR REPLACE VIEW ops.v_scout_payments_report_ui' in statement:
                try:
                    session.execute(text(statement))
                    session.commit()
                    print(f"  [OK] Vista ops.v_scout_payments_report_ui actualizada")
                except Exception as e:
                    print(f"  [ERROR] Error en statement {i}: {e}")
                    raise
        
        # Leer y ejecutar liquidation_ledger_scout.sql
        sql_file2 = Path(__file__).parent.parent / "sql" / "ops" / "liquidation_ledger_scout.sql"
        with open(sql_file2, 'r', encoding='utf-8') as f:
            sql_content2 = f.read()
        
        # Separar statements
        statements2 = []
        current_statement = []
        for line in sql_content2.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
            current_statement.append(line)
            if stripped.endswith(';'):
                statements2.append('\n'.join(current_statement))
                current_statement = []
        
        if current_statement:
            statements2.append('\n'.join(current_statement))
        
        for i, statement in enumerate(statements2, 1):
            if statement.strip() and 'CREATE OR REPLACE VIEW ops.v_scout_liquidation_open_items' in statement:
                try:
                    session.execute(text(statement))
                    session.commit()
                    print(f"  [OK] Vista ops.v_scout_liquidation_open_items actualizada")
                except Exception as e:
                    print(f"  [ERROR] Error en statement {i}: {e}")
                    raise
        
        # Verificaciones
        print("\n" + "=" * 80)
        print("2. VERIFICACIÓN 1: Conteo por attribution_confidence")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT attribution_confidence, COUNT(*) FROM ops.v_scout_liquidation_open_items GROUP BY 1 ORDER BY 2 DESC;")
        print("\nResultado:")
        print("-" * 80)
        
        query1 = text("""
            SELECT 
                attribution_confidence, 
                COUNT(*) 
            FROM ops.v_scout_liquidation_open_items 
            GROUP BY attribution_confidence 
            ORDER BY COUNT(*) DESC
        """)
        
        result1 = session.execute(query1)
        for row in result1:
            print(f"  {row.attribution_confidence:20s} | {row.count:10,}")
        
        print("\n" + "=" * 80)
        print("3. VERIFICACIÓN 2: Conteo de cabinet con acquisition_scout_id")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT COUNT(*) FROM ops.v_scout_liquidation_open_items WHERE lead_origin='cabinet' AND acquisition_scout_id IS NOT NULL;")
        print("\nResultado:")
        print("-" * 80)
        
        query2 = text("""
            SELECT COUNT(*) 
            FROM ops.v_scout_liquidation_open_items 
            WHERE lead_origin = 'cabinet' 
            AND acquisition_scout_id IS NOT NULL
        """)
        
        result2 = session.execute(query2)
        count = result2.scalar()
        print(f"  Total: {count:,}")
        
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN 3: 20 open items recientes con columnas de atribución")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT * FROM ops.v_scout_liquidation_open_items ORDER BY payable_date DESC LIMIT 20;")
        print("\nResultado:")
        print("-" * 80)
        
        query3 = text("""
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
            FROM ops.v_scout_liquidation_open_items 
            ORDER BY payable_date DESC 
            LIMIT 20
        """)
        
        result3 = session.execute(query3)
        rows3 = result3.fetchall()
        
        if rows3:
            print("\n  payment_item_key                    | person_key                         | lead_origin | scout_id | attr_scout_id | attr_scout_name              | confidence | rule")
            print("  " + "-" * 150)
            for row in rows3:
                scout_id_str = str(row.scout_id) if row.scout_id else "NULL"
                attr_scout_id_str = str(row.acquisition_scout_id) if row.acquisition_scout_id else "NULL"
                attr_scout_name_str = (row.acquisition_scout_name or "NULL")[:30]
                print(f"  {row.payment_item_key:35s} | {str(row.person_key):36s} | {row.lead_origin:11s} | {scout_id_str:8s} | {attr_scout_id_str:13s} | {attr_scout_name_str:30s} | {row.attribution_confidence:10s} | {row.attribution_rule}")
        else:
            print("\n  No hay open items")
        
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




















