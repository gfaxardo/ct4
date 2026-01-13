#!/usr/bin/env python
"""
Script para verificar datos del sistema Recovery Impact
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import SessionLocal
from sqlalchemy import text

def test_endpoint_query():
    """Probar la query que usa el endpoint"""
    print("=" * 80)
    print("VERIFICANDO QUERY DEL ENDPOINT")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Query que usa el endpoint
        result = db.execute(text("""
            SELECT
                COUNT(*) AS total_leads,
                COUNT(*) FILTER (WHERE impact_bucket = 'still_unidentified') AS unidentified_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'identified_but_missing_origin') AS identified_no_origin_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'recovered_within_14d_but_no_claim' OR impact_bucket = 'recovered_within_14d_and_claim') AS recovered_within_14d_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'recovered_late') AS recovered_late_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'recovered_within_14d_and_claim') AS recovered_within_14d_and_claim_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'identified_origin_no_claim') AS identified_origin_no_claim_count
            FROM ops.v_cabinet_identity_recovery_impact_14d
        """))
        
        row = result.fetchone()
        if row:
            print(f"\nTotal Leads: {row[0]}")
            print(f"Unidentified: {row[1]}")
            print(f"Identified no origin: {row[2]}")
            print(f"Recovered within 14d: {row[3]}")
            print(f"Recovered late: {row[4]}")
            print(f"Recovered with claim: {row[5]}")
            print(f"Identified origin no claim: {row[6]}")
            print("\n[OK] Query del endpoint funcionando correctamente")
        else:
            print("\n[ERROR] Query no retornó resultados")
            
    except Exception as e:
        print(f"\n[ERROR] Error en query: {e}")
    finally:
        db.close()

def verify_data():
    """Verificar datos en las vistas"""
    print("\n" + "=" * 80)
    print("VERIFICANDO DATOS EN VISTAS")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Distribución por impact_bucket
        result = db.execute(text("""
            SELECT impact_bucket, COUNT(*) as count 
            FROM ops.v_cabinet_identity_recovery_impact_14d 
            GROUP BY impact_bucket 
            ORDER BY count DESC
        """))
        print("\nDistribucion por impact_bucket:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        # Estadísticas generales
        result = db.execute(text("SELECT COUNT(*) FROM ops.cabinet_lead_recovery_audit"))
        print(f"\nRegistros en cabinet_lead_recovery_audit: {result.scalar()}")
        
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM ops.v_cabinet_lead_identity_effective 
            WHERE identity_effective = true
        """))
        print(f"Leads con identidad efectiva: {result.scalar()}")
        
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM ops.v_cabinet_lead_identity_effective 
            WHERE identity_effective = false
        """))
        print(f"Leads sin identidad efectiva: {result.scalar()}")
        
        print("\n[OK] Datos verificados correctamente")
        
    except Exception as e:
        print(f"\n[ERROR] Error verificando datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_endpoint_query()
    verify_data()
    print("\n" + "=" * 80)
    print("VERIFICACION COMPLETA")
    print("=" * 80)
