#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar los resultados del fix de is_reconcilable_enriched
Muestra los resultados de la auditoría de forma legible
"""
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.db import engine
    from sqlalchemy import text
except ImportError as e:
    print("ERROR: No se pueden importar los modulos necesarios.")
    print(f"\n   Error especifico: {e}")
    sys.exit(1)

def main():
    print("="*70)
    print("VERIFICACION DE RESULTADOS: is_reconcilable_enriched")
    print("="*70)
    
    try:
        with engine.connect() as conn:
            # 1. Resumen de PAID_MISAPPLIED por reconciliabilidad
            print("\n1. RESUMEN: PAID_MISAPPLIED por Reconciliabilidad")
            print("-"*70)
            result = conn.execute(text("""
                SELECT 
                    is_reconcilable_enriched,
                    COUNT(*) AS total_claims,
                    SUM(expected_amount) AS total_amount
                FROM ops.mv_yango_cabinet_claims_for_collection
                WHERE yango_payment_status = 'PAID_MISAPPLIED'
                GROUP BY is_reconcilable_enriched
                ORDER BY is_reconcilable_enriched DESC;
            """))
            rows = result.fetchall()
            if rows:
                for row in rows:
                    status = "RECONCILIABLE" if row[0] else "NO RECONCILIABLE"
                    print(f"  {status:20} {row[1]:>6} filas  S/ {row[2]:>12.2f}")
            else:
                print("  No hay datos")
            
            # 2. Verificación de que los montos cuadran
            print("\n2. VERIFICACION: Suma de Reconciliables + No Reconciliables = Total")
            print("-"*70)
            result = conn.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS reconcilable_rows,
                    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS not_reconcilable_rows,
                    (SELECT COUNT(*) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED') AS total_rows,
                    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS reconcilable_amount,
                    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = false) AS not_reconcilable_amount,
                    (SELECT SUM(expected_amount) FROM ops.mv_yango_cabinet_claims_for_collection WHERE yango_payment_status = 'PAID_MISAPPLIED') AS total_amount;
            """))
            row = result.fetchone()
            if row:
                data = dict(row._mapping)
                reconcilable_rows = data['reconcilable_rows'] or 0
                not_reconcilable_rows = data['not_reconcilable_rows'] or 0
                total_rows = data['total_rows'] or 0
                reconcilable_amount = float(data['reconcilable_amount'] or 0)
                not_reconcilable_amount = float(data['not_reconcilable_amount'] or 0)
                total_amount = float(data['total_amount'] or 0)
                
                suma_rows = reconcilable_rows + not_reconcilable_rows
                suma_amount = reconcilable_amount + not_reconcilable_amount
                
                print(f"  Reconciliables:        {reconcilable_rows:>6} filas  S/ {reconcilable_amount:>12.2f}")
                print(f"  No Reconciliables:     {not_reconcilable_rows:>6} filas  S/ {not_reconcilable_amount:>12.2f}")
                print(f"  Suma:                  {suma_rows:>6} filas  S/ {suma_amount:>12.2f}")
                print(f"  Total PAID_MISAPPLIED: {total_rows:>6} filas  S/ {total_amount:>12.2f}")
                
                rows_ok = (suma_rows == total_rows)
                amount_ok = abs(suma_amount - total_amount) < 0.01  # Tolerancia para decimales
                
                print(f"\n  Validacion filas:   {'OK' if rows_ok else 'ERROR'}")
                print(f"  Validacion montos:  {'OK' if amount_ok else 'ERROR'}")
                
                if rows_ok and amount_ok:
                    print("\n  RESULTADO: Los datos cuadran correctamente!")
                else:
                    print("\n  ADVERTENCIA: Los datos NO cuadran")
            
            # 3. Distribución por identity_status y match_confidence
            print("\n3. DISTRIBUCION: identity_status + match_confidence en PAID_MISAPPLIED")
            print("-"*70)
            result = conn.execute(text("""
                SELECT 
                    identity_status,
                    match_confidence,
                    match_rule,
                    is_reconcilable_enriched,
                    COUNT(*) AS total_claims,
                    SUM(expected_amount) AS total_amount
                FROM ops.mv_yango_cabinet_claims_for_collection
                WHERE yango_payment_status = 'PAID_MISAPPLIED'
                GROUP BY identity_status, match_confidence, match_rule, is_reconcilable_enriched
                ORDER BY is_reconcilable_enriched DESC, total_claims DESC;
            """))
            rows = result.fetchall()
            if rows:
                print(f"  {'identity_status':<15} {'match_conf':<10} {'match_rule':<15} {'reconcilable':<12} {'claims':>6} {'amount':>12}")
                print("  " + "-"*70)
                for row in rows:
                    print(f"  {str(row[0] or 'NULL'):<15} {str(row[1] or 'NULL'):<10} {str(row[2] or 'NULL'):<15} {str(row[3]):<12} {row[4]:>6} S/ {row[5]:>10.2f}")
            
            # 4. Ejemplos de reconciliables
            print("\n4. EJEMPLOS: Claims Reconciliables (TOP 5)")
            print("-"*70)
            result = conn.execute(text("""
                SELECT 
                    driver_id,
                    milestone_value,
                    expected_amount,
                    identity_status,
                    match_rule,
                    match_confidence,
                    is_reconcilable_enriched
                FROM ops.mv_yango_cabinet_claims_for_collection
                WHERE yango_payment_status = 'PAID_MISAPPLIED'
                    AND is_reconcilable_enriched = true
                ORDER BY expected_amount DESC
                LIMIT 5;
            """))
            rows = result.fetchall()
            if rows:
                for i, row in enumerate(rows, 1):
                    print(f"  {i}. Driver: {row[0]}, Milestone: {row[1]}, Amount: S/ {row[2]:.2f}")
                    print(f"     identity_status: {row[3]}, match_rule: {row[4]}, match_confidence: {row[5]}")
            else:
                print("  No hay claims reconciliables")
            
            print("\n" + "="*70)
            print("VERIFICACION COMPLETADA")
            print("="*70)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())















