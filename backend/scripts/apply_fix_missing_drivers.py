"""
Script para aplicar el fix de drivers faltantes en v_cabinet_financial_14d.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db
from sqlalchemy import text

def main():
    db = next(get_db())
    
    print("=" * 80)
    print("APLICANDO FIX: Incluir drivers desde v_cabinet_leads_limbo en vista principal")
    print("=" * 80)
    
    # Leer el SQL de la vista
    sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql', 'ops', 'v_cabinet_financial_14d.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Ejecutar el SQL
    try:
        db.execute(text(sql_content))
        db.commit()
        print("\n[OK] Vista actualizada exitosamente")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error al actualizar vista: {e}")
        raise
    
    # Verificar que ahora los drivers faltantes aparecen
    print("\n" + "=" * 80)
    print("VERIFICACIÓN: Contar drivers antes y después del fix")
    print("=" * 80)
    
    result1 = db.execute(text("SELECT COUNT(*) FROM ops.v_cabinet_financial_14d"))
    count_after = result1.scalar()
    print(f"\nDrivers en vista principal después del fix: {count_after}")
    
    result2 = db.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo l 
        WHERE l.person_key IS NOT NULL 
          AND l.driver_id IS NOT NULL 
          AND l.trips_14d > 0 
          AND NOT EXISTS (
              SELECT 1 
              FROM ops.v_cabinet_financial_14d f 
              WHERE f.driver_id = l.driver_id
          )
    """))
    count_still_missing = result2.scalar()
    print(f"Leads con identity+driver+trips que AÚN NO están en vista principal: {count_still_missing}")
    
    if count_still_missing == 0:
        print("\n[OK] ¡ÉXITO! Todos los leads con identity+driver+trips ahora aparecen en la vista principal")
    else:
        print(f"\n[WARNING] Aún hay {count_still_missing} leads que no aparecen. Revisar lógica de la vista.")
    
    print("\n" + "=" * 80)
    print("FIX APLICADO")
    print("=" * 80)

if __name__ == "__main__":
    main()
