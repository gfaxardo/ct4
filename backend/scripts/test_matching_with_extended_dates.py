"""Script para probar matching con rango de fechas ampliado"""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from sqlalchemy import text
from app.services.matching import MatchingEngine, IdentityCandidateInput
from datetime import datetime, timedelta

def test_extended_date_range():
    """Prueba matching con rango de fechas ampliado en algunos leads no_identity"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("PRUEBA: Matching con Rango de Fechas Ampliado")
        print("=" * 80)
        
        # Obtener algunos leads no_identity que fallaron por DATE_OUT_OF_RANGE
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
            LIMIT 10
        """)
        
        result = db.execute(query)
        leads = result.fetchall()
        
        print(f"\nProbando {len(leads)} leads con rango ampliado...\n")
        
        matching_engine = MatchingEngine(db)
        matches_found = 0
        
        for lead in leads:
            lead_id = lead.external_id or str(lead.id)
            plate_raw = lead.asset_plate_number
            first_name = lead.first_name or ""
            last_name = lead.last_name or ""
            name_raw = f"{first_name} {last_name}".strip()
            lead_date = lead.lead_created_at
            
            if not plate_raw or not name_raw:
                continue
            
            # Crear candidate
            from app.services.normalization import normalize_plate, normalize_name
            
            plate_norm = normalize_plate(plate_raw)
            name_norm = normalize_name(name_raw)
            
            if not plate_norm or not name_norm:
                continue
            
            candidate = IdentityCandidateInput(
                source_table="module_ct_cabinet_leads",
                source_pk=lead_id,
                snapshot_date=lead_date if isinstance(lead_date, datetime) else datetime.combine(lead_date, datetime.min.time()),
                park_id=None,
                phone_norm=None,
                license_norm=None,
                plate_norm=plate_norm,
                name_norm=name_norm,
                brand_norm=None,
                model_norm=None
            )
            
            # Intentar matching
            match_result = matching_engine.match_person(candidate)
            
            if match_result.person_key:
                matches_found += 1
                print(f"[OK] {lead_id}: Matched con {match_result.rule} (score: {match_result.score}, confidence: {match_result.confidence})")
            else:
                print(f"[X] {lead_id}: {match_result.reason_code}")
        
        print("\n" + "=" * 80)
        print(f"RESULTADO: {matches_found}/{len(leads)} leads matcheados con rango ampliado")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error en prueba: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_extended_date_range()
