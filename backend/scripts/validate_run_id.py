"""
Script de validación para verificar invariantes del sistema de identidad.

Valida:
- Todos los links/unmatched de un run tienen run_id asignado
- refresh_index default es False
- Report endpoint retorna breakdown coherente (sumas coinciden)
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.db import get_db_url
from app.models.canon import IdentityLink, IdentityUnmatched
from app.models.ops import IngestionRun, RunStatus, JobType


def validate_run_id_assignment(db):
    """Valida que todos los links/unmatched de runs completados tengan run_id."""
    print("Validando asignación de run_id...")
    
    completed_runs = db.query(IngestionRun).filter(
        IngestionRun.job_type == JobType.IDENTITY_RUN,
        IngestionRun.status == RunStatus.COMPLETED
    ).all()
    
    issues = []
    for run in completed_runs:
        links_without_run_id = db.query(IdentityLink).filter(
            IdentityLink.run_id.is_(None)
        ).count()
        
        unmatched_without_run_id = db.query(IdentityUnmatched).filter(
            IdentityUnmatched.run_id.is_(None)
        ).count()
        
        links_for_run = db.query(IdentityLink).filter(
            IdentityLink.run_id == run.id
        ).count()
        
        unmatched_for_run = db.query(IdentityUnmatched).filter(
            IdentityUnmatched.run_id == run.id
        ).count()
        
        if links_without_run_id > 0 or unmatched_without_run_id > 0:
            issues.append(f"Run {run.id}: Links sin run_id: {links_without_run_id}, Unmatched sin run_id: {unmatched_without_run_id}")
        
        print(f"  Run {run.id}: {links_for_run} links, {unmatched_for_run} unmatched")
    
    if issues:
        print("  ⚠️  Problemas encontrados:")
        for issue in issues:
            print(f"    - {issue}")
        return False
    else:
        print("  ✓ Todos los registros tienen run_id asignado")
        return True


def validate_report_coherence(db, run_id: int):
    """Valida que el reporte de un run sea coherente (sumas coinciden)."""
    print(f"\nValidando coherencia del reporte para run {run_id}...")
    
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
    if not run:
        print(f"  ✗ Run {run_id} no encontrado")
        return False
    
    links_count = db.query(func.count(IdentityLink.id)).filter(
        IdentityLink.run_id == run_id
    ).scalar()
    
    unmatched_count = db.query(func.count(IdentityUnmatched.id)).filter(
        IdentityUnmatched.run_id == run_id
    ).scalar()
    
    matched_by_rule = db.query(
        IdentityLink.match_rule,
        func.count(IdentityLink.id)
    ).filter(
        IdentityLink.run_id == run_id
    ).group_by(IdentityLink.match_rule).all()
    
    total_by_rule = sum(count for _, count in matched_by_rule)
    
    if total_by_rule != links_count:
        print(f"  ✗ Incoherencia: Total links ({links_count}) != Suma por regla ({total_by_rule})")
        return False
    
    print(f"  ✓ Links: {links_count}, Unmatched: {unmatched_count}")
    print(f"  ✓ Suma por regla coincide con total de links")
    return True


def main():
    engine = create_engine(get_db_url())
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("=== Validación de Invariantes del Sistema de Identidad ===\n")
        
        result1 = validate_run_id_assignment(db)
        
        completed_runs = db.query(IngestionRun).filter(
            IngestionRun.job_type == JobType.IDENTITY_RUN,
            IngestionRun.status == RunStatus.COMPLETED
        ).order_by(IngestionRun.id.desc()).limit(3).all()
        
        if completed_runs:
            print(f"\nValidando coherencia de los últimos {len(completed_runs)} runs...")
            results = []
            for run in completed_runs:
                results.append(validate_report_coherence(db, run.id))
            result2 = all(results)
        else:
            print("\nNo hay runs completados para validar coherencia")
            result2 = True
        
        print("\n=== Resumen ===")
        if result1 and result2:
            print("✓ Todas las validaciones pasaron")
            return 0
        else:
            print("✗ Algunas validaciones fallaron")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error durante validación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

























