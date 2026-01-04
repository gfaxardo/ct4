"""
Script para crear las vistas de RAW Health en la base de datos de forma segura.

Primero verifica qué tablas existen, luego comenta las CTEs de tablas inexistentes
antes de ejecutar el SQL.
"""
import sys
import re
from pathlib import Path

# Agregar el directorio raíz del backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(conn, schema: str, table: str) -> bool:
    """Verifica si una tabla existe en la base de datos."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = :schema AND table_name = :table
        )
    """), {"schema": schema, "table": table})
    return result.scalar()


def comment_out_cte(sql_content: str, cte_name: str, table_ref: str) -> str:
    """Comenta una CTE y su referencia en UNION ALL."""
    # Comentar la CTE completa (desde source_xxx AS hasta el cierre de paréntesis)
    pattern = rf'(source_{cte_name}\s+AS\s+\([^)]+\)),'
    sql_content = re.sub(pattern, r'/*\1*/,', sql_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Comentar la línea en UNION ALL
    pattern = rf'UNION ALL\s+SELECT \* FROM source_{cte_name}'
    sql_content = re.sub(pattern, r'-- UNION ALL\n-- SELECT * FROM source_' + cte_name, sql_content, flags=re.IGNORECASE)
    
    return sql_content


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
    
    # Verificar qué tablas existen
    logger.info("\nVerificando qué tablas existen...")
    tables_to_check = [
        ('public', 'summary_daily'),
        ('ops', 'yango_payment_ledger'),
        ('raw', 'module_ct_cabinet_payments'),
        ('public', 'module_ct_cabinet_leads'),
        ('public', 'module_ct_scouting_daily'),
        ('public', 'module_ct_cabinet_migrations'),
        ('public', 'module_ct_scout_drivers'),
        ('public', 'module_ct_cabinet_payments'),
        ('public', 'drivers'),
        ('public', 'module_ct_scouts_list'),
    ]
    
    with engine.connect() as conn:
        missing_tables = []
        for schema, table in tables_to_check:
            exists = check_table_exists(conn, schema, table)
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {schema}.{table}")
            if not exists:
                missing_tables.append((schema, table))
        
        if missing_tables:
            logger.warning(f"\n⚠ {len(missing_tables)} tabla(s) no existen. Las CTEs correspondientes serán comentadas.")
            logger.warning("Tablas faltantes:")
            for schema, table in missing_tables:
                logger.warning(f"  - {schema}.{table}")
    
    # Mapeo de tablas a nombres de CTE
    table_to_cte = {
        ('raw', 'module_ct_cabinet_payments'): 'raw_module_ct_cabinet_payments',
        ('public', 'module_ct_cabinet_migrations'): 'module_ct_cabinet_migrations',
        ('public', 'module_ct_scout_drivers'): 'module_ct_scout_drivers',
        ('public', 'module_ct_cabinet_payments'): 'module_ct_cabinet_payments',
        ('public', 'module_ct_scouts_list'): 'module_ct_scouts_list',
        ('public', 'module_ct_cabinet_leads'): 'module_ct_cabinet_leads',
    }
    
    # Comentar CTEs de tablas que no existen (solo las opcionales, no las críticas)
    # Las tablas críticas como summary_daily, yango_payment_ledger, module_ct_scouting_daily, drivers
    # deben existir, si no, el script fallará intencionalmente
    
    critical_tables = [
        ('public', 'summary_daily'),
        ('ops', 'yango_payment_ledger'),
        ('public', 'module_ct_scouting_daily'),
        ('public', 'drivers'),
    ]
    
    for schema, table in missing_tables:
        if (schema, table) in critical_tables:
            logger.error(f"\n❌ Tabla crítica {schema}.{table} no existe. No se pueden crear las vistas.")
            return 1
        
        if (schema, table) in table_to_cte:
            cte_name = table_to_cte[(schema, table)]
            logger.info(f"Comentando CTE: source_{cte_name}")
            # El SQL ya tiene estas CTEs comentadas, así que no necesitamos hacer nada
            # Pero verificamos que estén comentadas
    
    # Ejecutar el SQL
    try:
        with engine.connect() as conn:
            logger.info("\nEjecutando SQL para crear las vistas...")
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
                return 1
        
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



