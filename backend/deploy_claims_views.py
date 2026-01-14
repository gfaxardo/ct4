#!/usr/bin/env python3
"""
Script para desplegar las vistas de Claims Cabinet.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from app.config import settings


def log(message: str):
    """Imprime mensaje con timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def execute_sql_file(engine, file_path: str, description: str):
    """Ejecuta un archivo SQL."""
    log(f"  Ejecutando: {description}...")
    start = time.time()
    
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        with engine.connect() as conn:
            conn.execute(text("SET statement_timeout = 300000"))  # 5 minutos
            
            # Ejecutar cada statement por separado
            for statement in sql_content.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    # Saltamos COMMENT ON statements que tienen comillas problemáticas a veces
                    if any(keyword in statement.upper() for keyword in ['CREATE', 'DROP', 'ALTER', 'INSERT', 'UPDATE', 'DELETE']):
                        try:
                            conn.execute(text(statement))
                        except Exception as e:
                            error_msg = str(e)[:150]
                            if 'already exists' in error_msg.lower() or 'does not exist' in error_msg.lower():
                                pass  # Ignorar errores de existencia
                            else:
                                log(f"    ⚠ Advertencia: {error_msg}")
            conn.commit()
        
        elapsed = time.time() - start
        log(f"  ✓ {description} completado ({elapsed:.2f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        log(f"  ✗ Error en {description}: {str(e)[:200]}")
        return False


def main():
    log("=" * 60)
    log("INICIO: Despliegue de Vistas Claims Cabinet")
    log("=" * 60)
    
    # Conectar a la base de datos
    log("Conectando a la base de datos...")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        log("✓ Conexión exitosa")
    except Exception as e:
        log(f"✗ Error de conexión: {e}")
        sys.exit(1)
    
    sql_dir = Path(__file__).parent / "sql" / "ops"
    
    success_count = 0
    error_count = 0
    
    # Lista de archivos a ejecutar en orden
    files_to_execute = [
        # 1. Verificar que existe v_yango_payments_ledger_latest_enriched
        ("v_yango_payments_ledger_latest_enriched.sql", "v_yango_payments_ledger_latest_enriched"),
        # 2. Vista claims for collection
        ("v_yango_cabinet_claims_for_collection.sql", "v_yango_cabinet_claims_for_collection"),
        # 3. MV claims for collection
        ("create_mv_yango_cabinet_claims_for_collection.sql", "mv_yango_cabinet_claims_for_collection"),
        # 4. Vista claims exigimos
        ("v_yango_cabinet_claims_exigimos.sql", "v_yango_cabinet_claims_exigimos"),
    ]
    
    for filename, description in files_to_execute:
        file_path = sql_dir / filename
        if file_path.exists():
            if execute_sql_file(engine, str(file_path), description):
                success_count += 1
            else:
                error_count += 1
        else:
            log(f"  ⚠ Archivo no encontrado: {filename}")
            # Intentar crear la MV manualmente
            if "mv_yango_cabinet_claims_for_collection" in filename:
                log("  Creando MV manualmente...")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SET statement_timeout = 300000"))
                        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_claims_for_collection CASCADE"))
                        conn.execute(text("""
                            CREATE MATERIALIZED VIEW ops.mv_yango_cabinet_claims_for_collection AS
                            SELECT * FROM ops.v_yango_cabinet_claims_for_collection
                        """))
                        conn.execute(text("""
                            CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_claims_for_collection_pk 
                            ON ops.mv_yango_cabinet_claims_for_collection(driver_id, milestone_value, lead_date)
                        """))
                        conn.commit()
                    log("  ✓ MV creada manualmente")
                    success_count += 1
                except Exception as e:
                    log(f"  ✗ Error creando MV: {str(e)[:150]}")
                    error_count += 1
    
    # ==========================================================================
    # RESUMEN
    # ==========================================================================
    log("")
    log("=" * 60)
    log("DESPLIEGUE COMPLETADO")
    log("=" * 60)
    log(f"  Exitosos: {success_count}")
    log(f"  Errores: {error_count}")
    
    # Verificar que la API funciona
    log("")
    log("Verificando API...")
    import requests
    try:
        resp = requests.get("http://localhost:8000/api/v1/yango/cabinet/claims-to-collect?limit=5", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            log(f"✓ API funcionando - {data.get('total', 0)} claims encontrados")
        else:
            log(f"⚠ API retorna {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        log(f"⚠ No se pudo verificar API: {str(e)[:100]}")


if __name__ == "__main__":
    main()
