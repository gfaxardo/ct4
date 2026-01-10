#!/usr/bin/env python3
"""
Job Recurrente: Scout Attribution Refresh
==========================================
Ejecuta refresh de scout attribution cada 4 horas (configurable).

USO:
    # Ejecutar una vez ahora
    python backend/scripts/ops_refresh_scout_attribution.py
    
    # Ejecutar como cron job (cada 4 horas)
    0 */4 * * * cd /path/to/CT4 && python backend/scripts/ops_refresh_scout_attribution.py >> /var/log/scout_refresh.log 2>&1
"""

import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Reutilizar script run_once usando importlib para evitar problemas de path
import importlib.util
run_script_path = Path(__file__).parent / "run_scout_attribution_refresh.py"
spec = importlib.util.spec_from_file_location("run_scout_attribution_refresh", run_script_path)
run_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_module)
main = run_module.main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import io
    # Configurar encoding UTF-8 para Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    try:
        result = main()
        print(f"[OK] Scout attribution refresh completado (run_id={result['run_id']})")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Error en scout attribution refresh: {e}")
        sys.exit(1)

