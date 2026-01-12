#!/usr/bin/env python3
"""
Script para ejecutar los scripts SQL de enriquecimiento de scout attribution.
Ejecuta en orden:
1. v_scout_attribution_raw_ENRICHED.sql (agregar cabinet_payments)
2. v_yango_collection_with_scout_ENRICHED.sql (usar vista canónica + scout_name)
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Agregar el directorio backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def execute_sql_file(session, sql_file_path: Path):
    """Ejecuta un archivo SQL completo."""
    print(f"\n{'='*80}")
    print(f"Ejecutando: {sql_file_path.name}")
    print(f"{'='*80}\n")
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Remover queries de validación (SELECT que solo muestran resultados)
        # Buscar el marcador "-- ============================================================================"
        # y remover todo desde "QUERY DE VERIFICACIÓN" hasta el final
        lines = sql_content.split('\n')
        filtered_lines = []
        skip_section = False
        in_validation = False
        
        for i, line in enumerate(lines):
            # Detectar inicio de sección de validación
            if '-- ============================================================================' in line and i > 0:
                # Revisar líneas siguientes para ver si es sección de validación
                next_lines = lines[i+1:i+5]
                if any('QUERY DE VERIFICACIÓN' in l or 'VALIDACIÓN' in l or 'COBERTURA' in l for l in next_lines):
                    skip_section = True
                    continue
            # Si estamos en sección de validación, saltar hasta encontrar comentario de fin o siguiente sección
            if skip_section:
                if line.strip().startswith('-- ============================================================================'):
                    # Fin de sección de validación, empezar a incluir líneas de nuevo
                    skip_section = False
                continue
            
            filtered_lines.append(line)
        
        # Reconstruir SQL sin queries de validación
        sql_filtered = '\n'.join(filtered_lines)
        
        # También remover queries SELECT sueltas al final
        # Dividir por ';' y filtrar SELECT que no sean CREATE VIEW
        parts = sql_filtered.split(';')
        filtered_parts = []
        for part in parts:
            part_stripped = part.strip()
            # Incluir solo si no es SELECT de validación
            if part_stripped and not (part_stripped.upper().startswith('SELECT') and ('COUNT(*)' in part_stripped.upper() or 'GROUP BY' in part_stripped.upper())):
                filtered_parts.append(part_stripped)
        
        sql_filtered = ';'.join(filtered_parts) + ';' if filtered_parts else sql_filtered
        
        # Ejecutar todo el SQL de una vez
        session.execute(text(sql_filtered))
        session.commit()
        print(f"[OK] {sql_file_path.name} ejecutado exitosamente")
        return True
        
    except Exception as e:
        session.rollback()
        error_msg = str(e)
        # Algunos errores son esperados (como DROP VIEW IF EXISTS cuando no existe)
        if "does not exist" in error_msg.lower() or "cascade" in error_msg.lower():
            print(f"[WARN] Advertencia (posiblemente esperada): {error_msg[:300]}")
            try:
                # Intentar commit de todos modos si es un error esperado
                session.commit()
                return True
            except:
                pass
        print(f"\n[ERROR] Error ejecutando {sql_file_path.name}: {error_msg[:500]}")
        raise

def execute_validation_queries(session):
    """Ejecuta queries de validación para verificar los cambios."""
    print(f"\n{'='*80}")
    print("VALIDACIÓN: Cobertura de scout en cobranza Yango")
    print(f"{'='*80}\n")
    
    try:
        # Query 1: Cobertura general
        query1 = text("""
            SELECT 
                COUNT(*) AS total_claims,
                COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
                COUNT(*) FILTER (WHERE is_scout_resolved = false) AS claims_without_scout,
                ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2) AS pct_with_scout
            FROM ops.v_yango_collection_with_scout
        """)
        
        result1 = session.execute(query1).fetchone()
        if result1:
            print("Cobertura General:")
            print(f"  Total claims: {result1.total_claims:,}")
            print(f"  Con scout: {result1.claims_with_scout:,} ({result1.pct_with_scout}%)")
            print(f"  Sin scout: {result1.claims_without_scout:,} ({100 - result1.pct_with_scout}%)")
        
        # Query 2: Distribución por fuente
        query2 = text("""
            SELECT 
                scout_source_table,
                COUNT(*) AS claim_count,
                ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout WHERE is_scout_resolved = true), 0) * 100, 2) AS pct
            FROM ops.v_yango_collection_with_scout
            WHERE is_scout_resolved = true
            GROUP BY scout_source_table
            ORDER BY claim_count DESC
        """)
        
        result2 = session.execute(query2).fetchall()
        if result2:
            print("\nDistribucion por Fuente:")
            for row in result2:
                print(f"  {row.scout_source_table or 'NULL'}: {row.claim_count:,} ({row.pct}%)")
        
        # Query 3: Distribución por quality bucket
        query3 = text("""
            SELECT 
                scout_quality_bucket,
                COUNT(*) AS claim_count,
                ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout), 0) * 100, 2) AS pct
            FROM ops.v_yango_collection_with_scout
            GROUP BY scout_quality_bucket
            ORDER BY claim_count DESC
        """)
        
        result3 = session.execute(query3).fetchall()
        if result3:
            print("\nDistribucion por Quality Bucket:")
            for row in result3:
                print(f"  {row.scout_quality_bucket}: {row.claim_count:,} ({row.pct}%)")
        
        # Query 4: Verificar scout_name
        query4 = text("""
            SELECT 
                COUNT(*) FILTER (WHERE scout_name IS NOT NULL) AS with_scout_name,
                COUNT(*) FILTER (WHERE scout_id IS NOT NULL AND scout_name IS NULL) AS with_scout_id_but_no_name
            FROM ops.v_yango_collection_with_scout
            WHERE is_scout_resolved = true
        """)
        
        result4 = session.execute(query4).fetchone()
        if result4:
            print(f"\nEnriquecimiento con scout_name:")
            print(f"  Con scout_name: {result4.with_scout_name:,}")
            print(f"  Con scout_id pero sin scout_name: {result4.with_scout_id_but_no_name:,}")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\n[WARN] Error ejecutando queries de validacion: {e}")

def main():
    """Ejecuta los scripts SQL en orden."""
    scripts_dir = Path(__file__).parent / "sql"
    
    scripts = [
        scripts_dir / "10_create_v_scout_attribution_raw_ENRICHED.sql",
        scripts_dir / "11_create_v_scout_attribution.sql",  # Recrea v_scout_attribution desde la versión enriquecida
        scripts_dir / "04_yango_collection_with_scout_ENRICHED.sql",
    ]
    
    # Verificar que los archivos existen
    for script in scripts:
        if not script.exists():
            print(f"[ERROR] Archivo no encontrado: {script}")
            return 1
    
    # Conectar a la base de datos
    print(f"\nConectando a la base de datos...")
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Ejecutar scripts en orden
        for script in scripts:
            execute_sql_file(session, script)
        
        # Ejecutar queries de validación
        execute_validation_queries(session)
        
        print("\n[OK] Todos los scripts ejecutados exitosamente!")
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())
