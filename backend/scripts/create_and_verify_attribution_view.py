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
        print("1. CREANDO VISTA: ops.v_attribution_canonical")
        print("=" * 80)
        
        # Leer y ejecutar el SQL
        sql_file = Path(__file__).parent.parent / "sql" / "ops" / "v_attribution_canonical.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar el SQL completo (PostgreSQL puede manejar múltiples statements)
        # Separar por ; pero mantener el orden
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
        
        # Si queda algo sin terminar, agregarlo
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
        
        print("[OK] Vista creada exitosamente")
        
        # Verificaciones
        print("\n" + "=" * 80)
        print("2. VERIFICACIÓN 1: Conteo por attribution_confidence")
        print("=" * 80)
        
        query1 = text("""
            SELECT 
                attribution_confidence, 
                COUNT(*) AS count
            FROM ops.v_attribution_canonical 
            GROUP BY attribution_confidence 
            ORDER BY count DESC
        """)
        
        result1 = session.execute(query1)
        print("\n")
        for row in result1:
            print(f"  {row.attribution_confidence:15s} | {row.count:10,}")
        
        print("\n" + "=" * 80)
        print("3. VERIFICACIÓN 2: Conteo por lead_origin y attribution_confidence")
        print("=" * 80)
        
        query2 = text("""
            SELECT 
                lead_origin,
                attribution_confidence, 
                COUNT(*) AS count
            FROM ops.v_attribution_canonical 
            GROUP BY lead_origin, attribution_confidence 
            ORDER BY lead_origin, attribution_confidence
        """)
        
        result2 = session.execute(query2)
        print("\n")
        print("  lead_origin      | attribution_confidence | count")
        print("  " + "-" * 70)
        for row in result2:
            print(f"  {row.lead_origin:15s} | {row.attribution_confidence:22s} | {row.count:10,}")
        
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN 3: Muestra de medium/unknown (primeras 20 filas)")
        print("=" * 80)
        
        query3 = text("""
            SELECT 
                person_key,
                lead_origin,
                acquisition_scout_id,
                acquisition_scout_name,
                attribution_confidence,
                attribution_rule
            FROM ops.v_attribution_canonical 
            WHERE attribution_confidence IN ('medium', 'unknown')
            ORDER BY person_key 
            LIMIT 20
        """)
        
        result3 = session.execute(query3)
        rows3 = result3.fetchall()
        
        if rows3:
            print("\n")
            print("  person_key                             | lead_origin | scout_id | scout_name                    | confidence | rule")
            print("  " + "-" * 120)
            for row in rows3:
                scout_id_str = str(row.acquisition_scout_id) if row.acquisition_scout_id else "NULL"
                scout_name_str = (row.acquisition_scout_name or "NULL")[:30]
                print(f"  {str(row.person_key):36s} | {row.lead_origin:11s} | {scout_id_str:8s} | {scout_name_str:30s} | {row.attribution_confidence:10s} | {row.attribution_rule}")
        else:
            print("\n  No hay registros con confidence medium o unknown")
        
        print("\n" + "=" * 80)
        print("[OK] VERIFICACIONES COMPLETADAS")
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

