"""
Script para crear las vistas de RAW Health en la base de datos.

Usa la misma DATABASE_URL que el backend.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz del backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Crea las vistas de RAW Health en la base de datos."""
    
    # Mostrar la URL de conexión (sin password completo por seguridad)
    db_url_display = settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url
    logger.info(f"Conectando a: postgresql://...@{db_url_display}")
    
    # Crear engine
    engine = create_engine(settings.database_url)
    
    # Leer el archivo SQL
    sql_file = Path(__file__).parent.parent / "sql" / "ops" / "v_data_health.sql"
    
    if not sql_file.exists():
        logger.error(f"Archivo SQL no encontrado: {sql_file}")
        return 1
    
    logger.info(f"Leyendo archivo SQL: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    # Ejecutar el SQL
    try:
        with engine.connect() as conn:
            # Ejecutar el SQL completo
            logger.info("Ejecutando SQL para crear las vistas...")
            conn.execute(text(sql_content))
            conn.commit()
            logger.info("✓ SQL ejecutado exitosamente")
        
        # Verificar que las vistas existen
        logger.info("\nVerificando que las vistas existen...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    to_regclass('ops.v_data_freshness_status') as freshness,
                    to_regclass('ops.v_data_ingestion_daily') as ingestion,
                    to_regclass('ops.v_data_health_status') as health;
            """))
            row = result.fetchone()
            
            logger.info(f"  freshness: {row[0]}")
            logger.info(f"  ingestion: {row[1]}")
            logger.info(f"  health: {row[2]}")
            
            if all(row):
                logger.info("\n✓ Todas las vistas fueron creadas exitosamente")
            else:
                logger.warning("\n⚠ Algunas vistas no se crearon correctamente")
        
        # Probar SELECTs
        logger.info("\nProbando SELECTs...")
        with engine.connect() as conn:
            # Freshness
            result = conn.execute(text("SELECT * FROM ops.v_data_freshness_status LIMIT 1"))
            row = result.fetchone()
            if row:
                logger.info(f"✓ ops.v_data_freshness_status: {len(row)} columnas, primera fila OK")
            else:
                logger.warning("⚠ ops.v_data_freshness_status: sin datos")
            
            # Ingestion daily
            result = conn.execute(text("SELECT * FROM ops.v_data_ingestion_daily LIMIT 1"))
            row = result.fetchone()
            if row:
                logger.info(f"✓ ops.v_data_ingestion_daily: {len(row)} columnas, primera fila OK")
            else:
                logger.warning("⚠ ops.v_data_ingestion_daily: sin datos")
            
            # Health status
            result = conn.execute(text("SELECT * FROM ops.v_data_health_status LIMIT 1"))
            row = result.fetchone()
            if row:
                logger.info(f"✓ ops.v_data_health_status: {len(row)} columnas, primera fila OK")
            else:
                logger.warning("⚠ ops.v_data_health_status: sin datos")
        
        logger.info("\n✅ Proceso completado exitosamente")
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Error ejecutando SQL: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())







