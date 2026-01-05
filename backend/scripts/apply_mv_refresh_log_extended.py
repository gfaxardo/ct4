"""
Script para aplicar extensión de ops.mv_refresh_log
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
    sql_file = Path(__file__).parent.parent / "sql" / "ops" / "mv_refresh_log_extended.sql"
    
    logger.info(f"Leyendo SQL: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    with engine.connect() as conn:
        logger.info("Ejecutando SQL...")
        conn.execute(text(sql_content))
        conn.commit()
        logger.info("✓ Extensión de ops.mv_refresh_log aplicada")
    
    # Verificar columnas nuevas
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'ops' 
              AND table_name = 'mv_refresh_log'
              AND column_name IN ('refresh_started_at', 'refresh_finished_at', 'rows_after_refresh', 'host', 'meta')
            ORDER BY column_name
        """))
        columns = [row[0] for row in result]
        if len(columns) == 5:
            logger.info("✓ Verificación: todas las columnas nuevas existen")
            logger.info(f"  Columnas: {', '.join(columns)}")
        else:
            logger.warning(f"⚠ Verificación: solo {len(columns)}/5 columnas encontradas")
            logger.warning(f"  Columnas encontradas: {', '.join(columns) if columns else 'ninguna'}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



