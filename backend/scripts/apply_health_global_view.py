"""
Script para crear la vista ops.v_health_global
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    engine = create_engine(settings.database_url)
    sql_file = Path(__file__).parent.parent / "sql" / "ops" / "v_health_global.sql"
    
    logger.info(f"Leyendo SQL: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    with engine.connect() as conn:
        logger.info("Ejecutando SQL...")
        conn.execute(text(sql_content))
        conn.commit()
        logger.info("✓ Vista ops.v_health_global creada")
    
    # Verificar
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM pg_views 
                WHERE schemaname = 'ops' AND viewname = 'v_health_global'
            )
        """))
        exists = result.scalar()
        if exists:
            logger.info("✓ Verificación: vista existe")
            
            # Probar query
            result = conn.execute(text("SELECT * FROM ops.v_health_global"))
            row = result.fetchone()
            if row:
                logger.info(f"✓ Vista retorna estado global: {dict(row._mapping) if hasattr(row, '_mapping') else dict(row)}")
        else:
            logger.error("✗ Verificación: vista NO existe")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



