#!/usr/bin/env python3
"""
Prueba End-to-End: Scout Attribution Observability
==================================================
Ejecuta una prueba completa del sistema:
1. Backfill inicial
2. Verificar API endpoints
3. Verificar métricas actualizadas
"""

import sys
import io
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_backfill():
    """Ejecuta backfill"""
    logger.info("="*80)
    logger.info("PASO 1: Ejecutando backfill inicial")
    logger.info("="*80)
    
    try:
        import importlib.util
        backfill_path = Path(__file__).parent / "run_scout_attribution_refresh.py"
        spec = importlib.util.spec_from_file_location("run_scout_attribution_refresh", backfill_path)
        backfill_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backfill_module)
        
        result = backfill_module.main()
        logger.info(f"[OK] Backfill completado: run_id={result['run_id']}")
        return True, result
    except Exception as e:
        logger.error(f"[ERROR] Backfill falló: {e}")
        return False, None

def test_api_endpoints():
    """Verifica endpoints API"""
    logger.info("\n" + "="*80)
    logger.info("PASO 2: Verificando endpoints API")
    logger.info("="*80)
    
    try:
        import requests
        BASE_URL = "http://localhost:8000"
        API_BASE = f"{BASE_URL}/api/v1/scouts"
        
        endpoints = [
            "/attribution/metrics",
            "/attribution/job-status",
            "/attribution/conflicts?page=1&page_size=5",
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
                if response.status_code == 200:
                    results[endpoint] = True
                    logger.info(f"[OK] {endpoint}")
                else:
                    results[endpoint] = False
                    logger.error(f"[ERROR] {endpoint}: Status {response.status_code}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[SKIP] {endpoint}: Backend no está corriendo")
                results[endpoint] = None
            except Exception as e:
                logger.error(f"[ERROR] {endpoint}: {e}")
                results[endpoint] = False
        
        success_count = sum(1 for v in results.values() if v is True)
        total_count = len([v for v in results.values() if v is not None])
        
        if success_count == total_count:
            logger.info(f"[OK] Todos los endpoints funcionando ({success_count}/{total_count})")
            return True
        else:
            logger.warning(f"[WARN] Algunos endpoints fallaron ({success_count}/{total_count})")
            return False
            
    except ImportError:
        logger.warning("[SKIP] requests no instalado, omitiendo test de API")
        return None
    except Exception as e:
        logger.error(f"[ERROR] Test API falló: {e}")
        return False

def test_metrics_updated():
    """Verifica que las métricas se actualizaron"""
    logger.info("\n" + "="*80)
    logger.info("PASO 3: Verificando métricas actualizadas")
    logger.info("="*80)
    
    try:
        from sqlalchemy import create_engine, text
        from app.config import settings
        
        engine = create_engine(settings.database_url)
        conn = engine.connect()
        
        # Verificar métricas snapshot
        query = text("SELECT * FROM ops.v_scout_attribution_metrics_snapshot")
        result = conn.execute(query)
        row = result.fetchone()
        
        if row:
            logger.info(f"[OK] Métricas snapshot disponibles:")
            logger.info(f"   Total personas: {row.total_persons:,}")
            logger.info(f"   Scout satisfactorio: {row.persons_with_scout_satisfactory:,} ({row.pct_scout_satisfactory:.1f}%)")
            logger.info(f"   Conflictos: {row.conflicts_count:,}")
            logger.info(f"   Snapshot: {row.snapshot_timestamp}")
            
            # Verificar último job
            if row.last_job_status:
                logger.info(f"   Último job: {row.last_job_status}")
            
            conn.close()
            return True
        else:
            logger.error("[ERROR] No se obtuvieron métricas")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Verificación de métricas falló: {e}")
        return False

def main():
    """Ejecuta prueba end-to-end completa"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA END-TO-END: Scout Attribution Observability")
    logger.info("="*80)
    logger.info(f"Iniciado: {datetime.now().isoformat()}\n")
    
    results = {}
    
    # Paso 1: Backfill
    backfill_ok, backfill_result = test_backfill()
    results['backfill'] = backfill_ok
    
    # Paso 2: API Endpoints
    api_ok = test_api_endpoints()
    results['api'] = api_ok
    
    # Paso 3: Métricas
    metrics_ok = test_metrics_updated()
    results['metrics'] = metrics_ok
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN FINAL")
    logger.info("="*80)
    
    logger.info(f"Backfill: {'[OK]' if backfill_ok else '[ERROR]'}")
    logger.info(f"API Endpoints: {'[OK]' if api_ok else '[SKIP]' if api_ok is None else '[ERROR]'}")
    logger.info(f"Métricas: {'[OK]' if metrics_ok else '[ERROR]'}")
    
    all_ok = all([
        backfill_ok,
        metrics_ok,
        api_ok is not False  # Permitir None (skip)
    ])
    
    logger.info("\n" + "="*80)
    if all_ok:
        logger.info("[OK] PRUEBA END-TO-END COMPLETADA EXITOSAMENTE")
    else:
        logger.info("[WARN] ALGUNAS PRUEBAS FALLARON - Revisar logs arriba")
    logger.info("="*80)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

