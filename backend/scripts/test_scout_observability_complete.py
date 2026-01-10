#!/usr/bin/env python3
"""
Pruebas Finales: Scout Attribution Observability
================================================
Ejecuta todas las verificaciones y pruebas del sistema completo
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def test_sql_views():
    """Prueba que todas las vistas SQL existen y funcionan"""
    logger.info("="*80)
    logger.info("PRUEBA 1: Vistas SQL")
    logger.info("="*80)
    
    db = SessionLocal()
    results = {}
    
    views_to_test = [
        'ops.v_scout_attribution_metrics_snapshot',
        'ops.v_scout_attribution_metrics_daily',
        'ops.v_scout_attribution_raw',
        'ops.v_scout_attribution',
        'ops.v_scout_attribution_conflicts',
        'ops.v_persons_without_scout_categorized',
        'ops.v_yango_collection_with_scout',
        'ops.v_scout_payment_base',
    ]
    
    for view_name in views_to_test:
        try:
            query = text(f"SELECT COUNT(*) FROM {view_name}")
            result = db.execute(query)
            count = result.scalar()
            results[view_name] = {'exists': True, 'row_count': count}
            logger.info(f"✅ {view_name}: {count:,} filas")
        except Exception as e:
            results[view_name] = {'exists': False, 'error': str(e)}
            logger.error(f"❌ {view_name}: {str(e)[:100]}")
    
    db.close()
    return results

def test_audit_tables():
    """Prueba que las tablas de auditoría existen"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA 2: Tablas de Auditoría")
    logger.info("="*80)
    
    db = SessionLocal()
    results = {}
    
    tables_to_test = [
        'ops.identity_links_backfill_audit',
        'ops.lead_ledger_scout_backfill_audit',
        'ops.lead_events_scout_backfill_audit',
        'ops.ingestion_runs',
    ]
    
    for table_name in tables_to_test:
        try:
            query = text(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema || '.' || table_name = '{table_name}'
            """)
            result = db.execute(query)
            exists = result.scalar() > 0
            
            if exists:
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                count_result = db.execute(count_query)
                count = count_result.scalar()
                results[table_name] = {'exists': True, 'row_count': count}
                logger.info(f"✅ {table_name}: {count:,} registros")
            else:
                results[table_name] = {'exists': False}
                logger.warning(f"⚠️ {table_name}: No existe")
        except Exception as e:
            results[table_name] = {'exists': False, 'error': str(e)}
            logger.error(f"❌ {table_name}: {str(e)[:100]}")
    
    db.close()
    return results

def test_metrics_snapshot():
    """Prueba la vista de métricas instantáneas"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA 3: Métricas Instantáneas")
    logger.info("="*80)
    
    db = SessionLocal()
    
    try:
        query = text("""
            SELECT 
                total_persons,
                persons_with_scout_satisfactory,
                pct_scout_satisfactory,
                persons_missing_scout,
                conflicts_count,
                backlog_a_events_without_scout,
                backlog_d_scout_in_events_not_in_ledger,
                backlog_c_legacy_no_events_no_ledger,
                last_job_status,
                snapshot_timestamp
            FROM ops.v_scout_attribution_metrics_snapshot
        """)
        
        result = db.execute(query)
        row = result.fetchone()
        
        if row:
            logger.info(f"✅ Métricas obtenidas:")
            logger.info(f"   Total personas: {row.total_persons:,}")
            logger.info(f"   Scout satisfactorio: {row.persons_with_scout_satisfactory:,} ({row.pct_scout_satisfactory:.1f}%)")
            logger.info(f"   Missing scout: {row.persons_missing_scout:,}")
            logger.info(f"   Conflictos: {row.conflicts_count:,}")
            logger.info(f"   Backlog A: {row.backlog_a_events_without_scout:,}")
            logger.info(f"   Backlog C: {row.backlog_c_legacy_no_events_no_ledger:,}")
            logger.info(f"   Backlog D: {row.backlog_d_scout_in_events_not_in_ledger:,}")
            logger.info(f"   Último job: {row.last_job_status}")
            logger.info(f"   Snapshot: {row.snapshot_timestamp}")
            return {'success': True, 'metrics': dict(row._mapping)}
        else:
            logger.error("❌ No se obtuvieron métricas")
            return {'success': False}
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo métricas: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        db.close()

def test_scouting_daily_coverage():
    """Prueba cobertura de scouting_daily con identity_links"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA 4: Cobertura scouting_daily")
    logger.info("="*80)
    
    db = SessionLocal()
    
    try:
        query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS total_with_scout,
                COUNT(*) FILTER (
                    WHERE scout_id IS NOT NULL 
                    AND EXISTS (
                        SELECT 1 FROM canon.identity_links il
                        WHERE il.source_table = 'module_ct_scouting_daily'
                            AND il.source_pk = sd.id::TEXT
                    )
                ) AS with_identity
            FROM public.module_ct_scouting_daily sd
        """)
        
        result = db.execute(query)
        row = result.fetchone()
        
        if row:
            total = row.total_with_scout
            with_identity = row.with_identity
            pct = (with_identity / total * 100) if total > 0 else 0
            
            logger.info(f"✅ Scouting daily con scout_id: {total:,}")
            logger.info(f"✅ Con identity_links: {with_identity:,}")
            logger.info(f"✅ Porcentaje: {pct:.1f}%")
            
            if pct >= 99:
                logger.info("✅ EXCELENTE: Cobertura > 99%")
            elif pct >= 80:
                logger.info("⚠️ ADVERTENCIA: Cobertura 80-99%")
            else:
                logger.warning("❌ CRÍTICO: Cobertura < 80%")
            
            return {'success': True, 'total': total, 'with_identity': with_identity, 'pct': pct}
        else:
            return {'success': False}
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        db.close()

def test_conflicts_view():
    """Prueba vista de conflictos"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA 5: Vista de Conflictos")
    logger.info("="*80)
    
    db = SessionLocal()
    
    try:
        query = text("SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts")
        result = db.execute(query)
        count = result.scalar()
        
        logger.info(f"✅ Conflictos detectados: {count:,}")
        
        if count > 0:
            sample_query = text("""
                SELECT 
                    person_key,
                    distinct_scout_count,
                    scout_ids
                FROM ops.v_scout_attribution_conflicts
                LIMIT 5
            """)
            sample_result = db.execute(sample_query)
            logger.info("   Muestra de conflictos:")
            for row in sample_result.fetchall():
                logger.info(f"   - {row.person_key}: {row.distinct_scout_count} scouts {row.scout_ids}")
        
        return {'success': True, 'count': count}
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        db.close()

def test_yango_collection_with_scout():
    """Prueba vista de cobranza Yango con scout"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA 6: Cobranza Yango con Scout")
    logger.info("="*80)
    
    db = SessionLocal()
    
    try:
        query = text("""
            SELECT 
                COUNT(*) AS total_claims,
                COUNT(*) FILTER (WHERE is_scout_resolved = true) AS with_scout,
                COUNT(*) FILTER (WHERE is_scout_resolved = false) AS without_scout,
                ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2) AS pct_resolved
            FROM ops.v_yango_collection_with_scout
        """)
        
        result = db.execute(query)
        row = result.fetchone()
        
        if row:
            logger.info(f"✅ Total claims: {row.total_claims:,}")
            logger.info(f"✅ Con scout: {row.with_scout:,}")
            logger.info(f"✅ Sin scout: {row.without_scout:,}")
            logger.info(f"✅ % Resuelto: {row.pct_resolved:.1f}%")
            
            return {'success': True, 'metrics': dict(row._mapping)}
        else:
            return {'success': False}
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        db.close()

def test_verification_queries():
    """Ejecuta queries de verificación"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBA 7: Verificaciones Finales")
    logger.info("="*80)
    
    db = SessionLocal()
    
    try:
        # Verificar duplicados en v_scout_attribution
        query1 = text("""
            SELECT 
                COUNT(*) AS total_rows,
                COUNT(DISTINCT person_key) AS distinct_person_keys
            FROM ops.v_scout_attribution
        """)
        result1 = db.execute(query1)
        row1 = result1.fetchone()
        
        if row1.total_rows == row1.distinct_person_keys:
            logger.info(f"✅ v_scout_attribution: Sin duplicados ({row1.total_rows:,} filas, {row1.distinct_person_keys:,} person_keys)")
        else:
            logger.error(f"❌ v_scout_attribution: HAY DUPLICADOS ({row1.total_rows:,} filas, {row1.distinct_person_keys:,} person_keys)")
        
        # Verificar scout satisfactorio en lead_ledger
        query2 = text("""
            SELECT 
                COUNT(DISTINCT person_key) FILTER (WHERE attributed_scout_id IS NOT NULL) AS satisfactory_count,
                COUNT(DISTINCT person_key) AS total_ledger_entries
            FROM observational.lead_ledger
        """)
        result2 = db.execute(query2)
        row2 = result2.fetchone()
        
        logger.info(f"✅ Lead ledger scout satisfactorio: {row2.satisfactory_count:,} de {row2.total_ledger_entries:,}")
        
        return {
            'duplicates_check': row1.total_rows == row1.distinct_person_keys,
            'satisfactory_count': row2.satisfactory_count,
            'total_ledger': row2.total_ledger_entries
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        db.close()

def main():
    """Ejecuta todas las pruebas"""
    logger.info("\n" + "="*80)
    logger.info("PRUEBAS FINALES: Scout Attribution Observability")
    logger.info("="*80)
    logger.info(f"Iniciado: {datetime.now().isoformat()}\n")
    
    results = {}
    
    # Prueba 1: Vistas SQL
    results['views'] = test_sql_views()
    
    # Prueba 2: Tablas de auditoría
    results['audit_tables'] = test_audit_tables()
    
    # Prueba 3: Métricas
    results['metrics'] = test_metrics_snapshot()
    
    # Prueba 4: Cobertura scouting_daily
    results['scouting_coverage'] = test_scouting_daily_coverage()
    
    # Prueba 5: Conflictos
    results['conflicts'] = test_conflicts_view()
    
    # Prueba 6: Cobranza Yango
    results['yango_collection'] = test_yango_collection_with_scout()
    
    # Prueba 7: Verificaciones finales
    results['verifications'] = test_verification_queries()
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN FINAL")
    logger.info("="*80)
    
    all_views_ok = all(r.get('exists', False) for r in results['views'].values())
    all_tables_ok = all(r.get('exists', False) for r in results['audit_tables'].values())
    metrics_ok = results['metrics'].get('success', False)
    coverage_ok = results['scouting_coverage'].get('pct', 0) >= 80
    conflicts_ok = results['conflicts'].get('success', False)
    yango_ok = results['yango_collection'].get('success', False)
    verifications_ok = results['verifications'].get('duplicates_check', False)
    
    logger.info(f"Vistas SQL: {'✅ OK' if all_views_ok else '❌ ERROR'}")
    logger.info(f"Tablas Auditoría: {'✅ OK' if all_tables_ok else '❌ ERROR'}")
    logger.info(f"Métricas: {'✅ OK' if metrics_ok else '❌ ERROR'}")
    logger.info(f"Cobertura scouting_daily: {'✅ OK' if coverage_ok else '❌ ERROR'}")
    logger.info(f"Conflictos: {'✅ OK' if conflicts_ok else '❌ ERROR'}")
    logger.info(f"Cobranza Yango: {'✅ OK' if yango_ok else '❌ ERROR'}")
    logger.info(f"Verificaciones: {'✅ OK' if verifications_ok else '❌ ERROR'}")
    
    all_ok = all([
        all_views_ok,
        all_tables_ok,
        metrics_ok,
        coverage_ok,
        conflicts_ok,
        yango_ok,
        verifications_ok
    ])
    
    logger.info("\n" + "="*80)
    if all_ok:
        logger.info("✅ TODAS LAS PRUEBAS PASARON")
    else:
        logger.info("⚠️ ALGUNAS PRUEBAS FALLARON - Revisar logs arriba")
    logger.info("="*80)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

