"""
Script para verificar registros en ops.mv_refresh_log
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from sqlalchemy import create_engine, text

def main():
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM ops.mv_refresh_log 
            ORDER BY refreshed_at DESC 
            LIMIT 5
        """))
        rows = result.fetchall()
        
        print(f"Registros en ops.mv_refresh_log: {len(rows)}")
        print()
        
        if rows:
            for row in rows:
                print(f"  id: {row.id}")
                print(f"  refreshed_at: {row.refreshed_at}")
                print(f"  schema_name: {row.schema_name}")
                print(f"  mv_name: {row.mv_name}")
                print(f"  status: {row.status}")
                print(f"  duration_ms: {row.duration_ms}")
                print(f"  error_message: {row.error_message}")
                print()
        else:
            print("  (tabla vacía - aún no se han ejecutado refreshes)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


