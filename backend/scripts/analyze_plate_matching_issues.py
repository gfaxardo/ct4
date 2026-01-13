"""Script para analizar por qué el matching por placa falla"""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from sqlalchemy import text
from app.services.normalization import normalize_plate, normalize_name
from app.config import PARK_ID_OBJETIVO, NAME_SIMILARITY_THRESHOLD
from datetime import datetime, timedelta

def analyze_plate_matching_issues():
    """Analiza por qué el matching por placa no funciona para leads no_identity"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("ANÁLISIS: Por qué falla matching por placa (R3)")
        print("=" * 80)
        
        # Obtener leads no_identity con placa
        query = text("""
            SELECT 
                cl.external_id,
                cl.id,
                cl.lead_created_at,
                cl.first_name,
                cl.last_name,
                cl.asset_plate_number,
                v.gap_age_days
            FROM ops.v_identity_gap_analysis v
            JOIN public.module_ct_cabinet_leads cl ON (
                COALESCE(cl.external_id, cl.id::TEXT) = v.lead_id
            )
            WHERE v.gap_reason = 'no_identity'
              AND cl.asset_plate_number IS NOT NULL
              AND cl.asset_plate_number != ''
            ORDER BY v.gap_age_days DESC
            LIMIT 20
        """)
        
        result = db.execute(query)
        leads = result.fetchall()
        
        print(f"\nAnalizando {len(leads)} leads con placa...\n")
        
        issues = {
            'no_candidates': 0,
            'wrong_park': 0,
            'date_out_of_range': 0,
            'name_similarity_low': 0,
            'multiple_candidates': 0,
            'success': 0
        }
        
        for lead in leads:
            lead_id = lead.external_id or str(lead.id)
            plate_raw = lead.asset_plate_number
            first_name = lead.first_name or ""
            last_name = lead.last_name or ""
            name_raw = f"{first_name} {last_name}".strip()
            lead_date = lead.lead_created_at
            
            # Normalizar
            plate_norm = normalize_plate(plate_raw)
            name_norm = normalize_name(name_raw) if name_raw else None
            
            if not plate_norm or not name_norm:
                continue
            
            # Simular R3 matching
            date_from = lead_date - timedelta(days=30)
            date_to = lead_date + timedelta(days=7)
            
            # Paso 1: Buscar candidatos por placa
            check_query = text("""
                SELECT driver_id, park_id, full_name_norm, hire_date
                FROM canon.drivers_index
                WHERE plate_norm = :plate_norm
                LIMIT 20
            """)
            
            result = db.execute(check_query, {"plate_norm": plate_norm})
            all_candidates = result.fetchall()
            
            if not all_candidates:
                issues['no_candidates'] += 1
                print(f"[X] {lead_id}: NO_CANDIDATES (placa: {plate_norm})")
                continue
            
            # Paso 2: Filtrar por park_id
            park_candidates = [c for c in all_candidates if c.park_id == PARK_ID_OBJETIVO]
            
            if not park_candidates:
                issues['wrong_park'] += 1
                print(f"[!] {lead_id}: WRONG_PARK (placa: {plate_norm}, park: {all_candidates[0].park_id})")
                continue
            
            # Paso 3: Filtrar por fecha
            date_candidates = []
            for c in park_candidates:
                if c.hire_date is None:
                    date_candidates.append(c)
                else:
                    # Convertir hire_date a datetime si es date
                    hire_dt = c.hire_date
                    if isinstance(hire_dt, datetime):
                        pass
                    else:
                        from datetime import date as date_type
                        if isinstance(hire_dt, date_type):
                            hire_dt = datetime.combine(hire_dt, datetime.min.time())
                    
                    if date_from <= hire_dt <= date_to:
                        date_candidates.append(c)
            
            if not date_candidates:
                issues['date_out_of_range'] += 1
                print(f"[!] {lead_id}: DATE_OUT_OF_RANGE (placa: {plate_norm}, hire_date: {park_candidates[0].hire_date})")
                continue
            
            # Paso 4: Verificar similitud de nombres
            from app.services.normalization import name_similarity
            
            scored_candidates = []
            for c in date_candidates:
                similarity = name_similarity(name_norm, c.full_name_norm, NAME_SIMILARITY_THRESHOLD)
                if similarity >= NAME_SIMILARITY_THRESHOLD:
                    scored_candidates.append({
                        "driver_id": c.driver_id,
                        "similarity": similarity,
                        "name": c.full_name_norm
                    })
            
            if not scored_candidates:
                issues['name_similarity_low'] += 1
                best_sim = max([name_similarity(name_norm, c.full_name_norm, NAME_SIMILARITY_THRESHOLD) 
                               for c in date_candidates], default=0)
                print(f"[!] {lead_id}: NAME_SIMILARITY_LOW (placa: {plate_norm}, best: {best_sim:.2f}, threshold: {NAME_SIMILARITY_THRESHOLD})")
                continue
            
            if len(scored_candidates) > 1:
                issues['multiple_candidates'] += 1
                print(f"[!] {lead_id}: MULTIPLE_CANDIDATES (placa: {plate_norm}, {len(scored_candidates)} candidatos)")
            else:
                issues['success'] += 1
                print(f"[OK] {lead_id}: SUCCESS (placa: {plate_norm}, driver: {scored_candidates[0]['driver_id']}, sim: {scored_candidates[0]['similarity']:.2f})")
        
        print("\n" + "=" * 80)
        print("RESUMEN DE ISSUES:")
        print("=" * 80)
        for issue, count in issues.items():
            pct = 100 * count / len(leads) if leads else 0
            print(f"  {issue:25}: {count:3} ({pct:5.1f}%)")
        
        print("\nRECOMENDACIONES:")
        if issues['wrong_park'] > 0:
            print(f"  - {issues['wrong_park']} leads tienen candidatos pero en otro park_id")
            print("    -> Considerar matching cross-park si es valido")
        
        if issues['date_out_of_range'] > 0:
            print(f"  - {issues['date_out_of_range']} leads tienen candidatos pero hire_date fuera de rango")
            print("    -> PROBLEMA PRINCIPAL: Rango de fechas muy restrictivo (-30 a +7 dias)")
            print("    -> Solucion 1: Ampliar rango de fechas (ej: -90 a +30 dias)")
            print("    -> Solucion 2: Crear regla R3b sin restriccion de fecha (menor confianza)")
            print("    -> Solucion 3: Matching por placa sola si no hay candidatos en rango")
        
        if issues['name_similarity_low'] > 0:
            print(f"  - {issues['name_similarity_low']} leads tienen candidatos pero similitud de nombre baja")
            print(f"    -> Threshold actual: {NAME_SIMILARITY_THRESHOLD}")
            print("    -> Considerar bajar threshold o matching por placa sola (menor confianza)")
        
        if issues['no_candidates'] > 0:
            print(f"  - {issues['no_candidates']} leads NO tienen candidatos en drivers_index")
            print("    -> Estos leads no pueden matchear automaticamente")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    analyze_plate_matching_issues()
