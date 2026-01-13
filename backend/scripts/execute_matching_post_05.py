#!/usr/bin/env python3
"""
Script para ejecutar matching/ingestion de leads post-05/01/2026 directamente.
"""

import sys
import os
from pathlib import Path
from datetime import date

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.ingestion import IngestionService
from app.db import SessionLocal

# Configuración de base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

def main():
    """Ejecuta matching para leads post-05."""
    print("=" * 80)
    print("EJECUTANDO MATCHING PARA LEADS POST-05/01/2026")
    print("=" * 80)
    print()
    
    # Crear sesión de base de datos
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Crear servicio de ingestion
        service = IngestionService(db)
        
        print("Parámetros del job:")
        print(f"  - source_tables: ['module_ct_cabinet_leads']")
        print(f"  - scope_date_from: 2026-01-06")
        print(f"  - scope_date_to: 2026-01-10")
        print(f"  - incremental: True")
        print()
        print("Iniciando job de matching...")
        print("-" * 80)
        
        # Ejecutar ingestion
        run = service.run_ingestion(
            source_tables=['module_ct_cabinet_leads'],
            scope_date_from=date(2026, 1, 6),
            scope_date_to=date(2026, 1, 10),
            incremental=True,
            refresh_index=False
        )
        
        print()
        print("=" * 80)
        print("JOB COMPLETADO")
        print("=" * 80)
        print()
        print(f"Run ID: {run.id}")
        print(f"Status: {run.status}")
        print(f"Job Type: {run.job_type}")
        print()
        
        # Refrescar para obtener stats actualizados
        db.refresh(run)
        
        if hasattr(run, 'stats_json') and run.stats_json:
            stats = run.stats_json
            print("Estadísticas:")
            if 'cabinet_leads' in stats:
                cl_stats = stats['cabinet_leads']
                print(f"  - Procesados: {cl_stats.get('processed', 0)}")
                print(f"  - Matched: {cl_stats.get('matched', 0)}")
                print(f"  - Unmatched: {cl_stats.get('unmatched', 0)}")
                print(f"  - Skipped: {cl_stats.get('skipped', 0)}")
        
        print()
        print("=" * 80)
        print("VERIFICACION POST-FIX")
        print("=" * 80)
        print()
        print("Ejecuta el script de diagnóstico para verificar resultados:")
        print("  python backend/scripts/diagnose_post_05_leads.py")
        print()
        print("O ejecuta la auditoría semanal:")
        print("  python backend/scripts/install_and_test_audit_weekly.py")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
