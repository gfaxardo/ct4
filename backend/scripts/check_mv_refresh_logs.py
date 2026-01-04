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
            SELECT schema_name, mv_name, status, refreshed_at, duration_ms 
            FROM ops.mv_refresh_log 
            ORDER BY refreshed_at DESC 
            LIMIT 20
        """))
        rows = result.fetchall()
        
        print(f"Registros encontrados: {len(rows)}")
        print()
        
        for row in rows:
            print(f"  {row.schema_name}.{row.mv_name}: {row.status} - {row.refreshed_at} ({row.duration_ms}ms)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



