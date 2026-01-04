"""
Script para crear la tabla ops.mv_refresh_log
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
    sql_file = Path(__file__).parent.parent / "sql" / "ops" / "mv_refresh_log.sql"
    
    logger.info(f"Leyendo SQL: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    with engine.connect() as conn:
        logger.info("Ejecutando SQL...")
        conn.execute(text(sql_content))
        conn.commit()
        logger.info("✓ Tabla ops.mv_refresh_log creada")
    
    # Verificar
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'ops' AND table_name = 'mv_refresh_log'
            )
        """))
        exists = result.scalar()
        if exists:
            logger.info("✓ Verificación: tabla existe")
        else:
            logger.error("✗ Verificación: tabla NO existe")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



