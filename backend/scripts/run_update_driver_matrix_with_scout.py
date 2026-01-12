#!/usr/bin/env python3
"""
Script para actualizar v_payments_driver_matrix_cabinet con scout attribution.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

def main():
    scripts_dir = Path(__file__).parent.parent / "sql" / "ops"
    script_file = scripts_dir / "v_payments_driver_matrix_cabinet.sql"
    
    if not script_file.exists():
        print(f"[ERROR] Archivo no encontrado: {script_file}")
        return 1
    
    print(f"\n{'='*80}")
    print(f"Ejecutando: {script_file.name}")
    print(f"{'='*80}\n")
    
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Remover queries de validación/comentarios (SELECT que solo muestran resultados)
        lines = sql_content.split('\n')
        filtered_lines = []
        skip_validation = False
        
        for i, line in enumerate(lines):
            if 'QUERY DE VERIFICACIÓN' in line or 'VALIDACIÓN' in line or 'COBERTURA' in line:
                skip_validation = True
            if skip_validation:
                if line.strip().startswith('-- ============================================================================'):
                    skip_validation = False
                continue
            filtered_lines.append(line)
        
        sql_filtered = '\n'.join(filtered_lines)
        
        # Ejecutar SQL
        session.execute(text(sql_filtered))
        session.commit()
        
        print(f"[OK] {script_file.name} ejecutado exitosamente")
        
        # Validación rápida
        print(f"\n{'='*80}")
        print("VALIDACIÓN: Verificando vista actualizada")
        print(f"{'='*80}\n")
        
        check_query = text("""
            SELECT 
                COUNT(*) AS total_drivers,
                COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS drivers_with_scout,
                COUNT(*) FILTER (WHERE scout_name IS NOT NULL) AS drivers_with_scout_name
            FROM ops.v_payments_driver_matrix_cabinet
            LIMIT 1
        """)
        
        result = session.execute(check_query).fetchone()
        if result:
            print(f"Total drivers: {result.total_drivers:,}")
            print(f"Drivers con scout_id: {result.drivers_with_scout:,}")
            print(f"Drivers con scout_name: {result.drivers_with_scout_name:,}")
            print(f"\n[OK] Vista actualizada correctamente")
        
        return 0
        
    except Exception as e:
        session.rollback()
        error_msg = str(e)
        print(f"\n[ERROR] Error ejecutando {script_file.name}: {error_msg[:500]}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())
