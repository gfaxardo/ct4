"""Script para analizar leads no_identity y optimizar matching"""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from sqlalchemy import text
from collections import Counter

def analyze_no_identity_leads():
    """Analiza leads sin identidad para identificar patrones y oportunidades de matching"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("ANÁLISIS: Leads NO_IDENTITY (191 leads)")
        print("=" * 80)
        
        # 1. Obtener datos de los leads no_identity
        query = text("""
            SELECT 
                cl.external_id,
                cl.id,
                cl.lead_created_at,
                cl.park_phone,
                cl.first_name,
                cl.middle_name,
                cl.last_name,
                cl.asset_plate_number,
                v.gap_age_days,
                v.risk_level
            FROM ops.v_identity_gap_analysis v
            JOIN public.module_ct_cabinet_leads cl ON (
                COALESCE(cl.external_id, cl.id::TEXT) = v.lead_id
            )
            WHERE v.gap_reason = 'no_identity'
            ORDER BY v.gap_age_days DESC, v.risk_level DESC
        """)
        
        result = db.execute(query)
        leads = result.fetchall()
        
        print(f"\n1. TOTAL LEADS NO_IDENTITY: {len(leads)}")
        
        # 2. Análisis de datos disponibles
        print("\n2. ANÁLISIS DE DATOS DISPONIBLES:")
        
        has_phone = 0
        has_name = 0
        has_plate = 0
        has_phone_and_name = 0
        has_all = 0
        has_nothing = 0
        
        phone_patterns = Counter()
        name_patterns = Counter()
        
        for lead in leads:
            phone = lead.park_phone
            first_name = lead.first_name
            last_name = lead.last_name
            plate = lead.asset_plate_number
            
            # Contar qué datos tienen
            has_phone_val = phone and phone.strip() and len(phone.strip()) > 0
            has_name_val = (first_name and first_name.strip()) or (last_name and last_name.strip())
            has_plate_val = plate and plate.strip() and len(plate.strip()) > 0
            
            if has_phone_val:
                has_phone += 1
                # Analizar formato de teléfono
                phone_clean = phone.strip()
                if phone_clean.startswith('+'):
                    phone_patterns['+prefix'] += 1
                elif phone_clean.startswith('0'):
                    phone_patterns['0prefix'] += 1
                elif len(phone_clean) == 10:
                    phone_patterns['10digits'] += 1
                elif len(phone_clean) < 10:
                    phone_patterns['short'] += 1
                else:
                    phone_patterns['other'] += 1
            
            if has_name_val:
                has_name += 1
                # Analizar nombres
                if first_name and last_name:
                    name_patterns['first_last'] += 1
                elif first_name:
                    name_patterns['first_only'] += 1
                elif last_name:
                    name_patterns['last_only'] += 1
            
            if has_plate_val:
                has_plate += 1
            
            if has_phone_val and has_name_val:
                has_phone_and_name += 1
            
            if has_phone_val and has_name_val and has_plate_val:
                has_all += 1
            
            if not has_phone_val and not has_name_val and not has_plate_val:
                has_nothing += 1
        
        print(f"   Leads con teléfono: {has_phone} ({100*has_phone/len(leads):.1f}%)")
        print(f"   Leads con nombre: {has_name} ({100*has_name/len(leads):.1f}%)")
        print(f"   Leads con placa: {has_plate} ({100*has_plate/len(leads):.1f}%)")
        print(f"   Leads con teléfono Y nombre: {has_phone_and_name} ({100*has_phone_and_name/len(leads):.1f}%)")
        print(f"   Leads con todos los datos: {has_all} ({100*has_all/len(leads):.1f}%)")
        print(f"   Leads sin datos: {has_nothing} ({100*has_nothing/len(leads):.1f}%)")
        
        print("\n   Patrones de teléfono:")
        for pattern, count in phone_patterns.most_common():
            print(f"     {pattern:15}: {count:4} ({100*count/has_phone if has_phone > 0 else 0:.1f}%)")
        
        print("\n   Patrones de nombres:")
        for pattern, count in name_patterns.most_common():
            print(f"     {pattern:15}: {count:4} ({100*count/has_name if has_name > 0 else 0:.1f}%)")
        
        # 3. Verificar si hay candidatos en drivers_index
        print("\n3. VERIFICACIÓN DE CANDIDATOS EN DRIVERS_INDEX:")
        
        candidates_by_phone = 0
        candidates_by_plate = 0
        candidates_by_name = 0
        
        # Leads con teléfono
        leads_with_phone = [l for l in leads if l.park_phone and l.park_phone.strip()]
        if leads_with_phone:
            print(f"\n   Analizando {len(leads_with_phone)} leads con teléfono...")
            
            candidates_found = 0
            
            for lead in leads_with_phone[:50]:  # Muestra de 50
                phone = lead.park_phone.strip()
                
                # Normalizar teléfono
                from app.services.normalization import normalize_phone
                try:
                    phone_norm = normalize_phone(phone)
                    
                    # Buscar en drivers_index
                    check_query = text("""
                        SELECT COUNT(*) as count
                        FROM canon.drivers_index
                        WHERE phone_normalized = :phone_norm
                    """)
                    result = db.execute(check_query, {"phone_norm": phone_norm})
                    count = result.scalar()
                    
                    if count > 0:
                        candidates_by_phone += 1
                        candidates_found += 1
                except Exception as e:
                    pass
            
            if len(leads_with_phone) > 0:
                print(f"   Candidatos encontrados por teléfono (muestra 50): {candidates_by_phone}/50")
                print(f"   Estimado total: ~{candidates_by_phone * len(leads_with_phone) / 50:.0f} leads podrían matchear")
        
        # Leads con placa
        leads_with_plate = [l for l in leads if l.asset_plate_number and l.asset_plate_number.strip()]
        if leads_with_plate:
            print(f"\n   Analizando {len(leads_with_plate)} leads con placa...")
            
            for lead in leads_with_plate[:50]:  # Muestra de 50
                plate = lead.asset_plate_number.strip()
                
                # Normalizar placa (remover espacios, convertir a mayúsculas)
                plate_norm = plate.upper().replace(' ', '').replace('-', '')
                
                # Buscar en drivers_index (usar plate_norm como en matching.py)
                check_query = text("""
                    SELECT COUNT(*) as count
                    FROM canon.drivers_index
                    WHERE plate_norm = :plate_norm
                """)
                result = db.execute(check_query, {"plate_norm": plate_norm})
                count = result.scalar()
                
                if count > 0:
                    candidates_by_plate += 1
                # Rollback en caso de error para continuar
                try:
                    db.rollback()
                except:
                    pass
            
            print(f"   Candidatos encontrados por placa (muestra 50): {candidates_by_plate}/50")
            print(f"   Estimado total: ~{candidates_by_plate * len(leads_with_plate) / 50:.0f} leads podrían matchear")
        
        # Leads con nombre
        leads_with_name = [l for l in leads if (l.first_name and l.first_name.strip()) or (l.last_name and l.last_name.strip())]
        if leads_with_name:
            print(f"\n   Analizando {len(leads_with_name)} leads con nombre...")
            
            for lead in leads_with_name[:50]:  # Muestra de 50
                first_name = lead.first_name.strip() if lead.first_name else ""
                last_name = lead.last_name.strip() if lead.last_name else ""
                
                # Normalizar nombres
                from app.services.normalization import normalize_name
                try:
                    name_norm = normalize_name(f"{first_name} {last_name}".strip())
                    
                    # Buscar en drivers_index (búsqueda parcial)
                    check_query = text("""
                        SELECT COUNT(*) as count
                        FROM canon.drivers_index
                        WHERE name_normalized LIKE :name_pattern
                           OR name_normalized LIKE :name_pattern2
                    """)
                    result = db.execute(check_query, {
                        "name_pattern": f"%{name_norm}%",
                        "name_pattern2": f"%{name_norm.split()[0] if name_norm.split() else ''}%"
                    })
                    count = result.scalar()
                    
                    if count > 0:
                        candidates_by_name += 1
                except Exception as e:
                    pass
            
            print(f"   Candidatos encontrados por nombre (muestra 50): {candidates_by_name}/50")
            print(f"   Estimado total: ~{candidates_by_name * len(leads_with_name) / 50:.0f} leads podrían matchear")
        
        # 4. Análisis de jobs fallidos
        print("\n4. ANÁLISIS DE JOBS FALLIDOS:")
        
        try:
            failed_query = text("""
                SELECT 
                    imj.fail_reason,
                    COUNT(*) as count,
                    AVG(imj.attempt_count)::int as avg_attempts
                FROM ops.identity_matching_jobs imj
                JOIN ops.v_identity_gap_analysis v ON v.lead_id = imj.source_id
                WHERE v.gap_reason = 'no_identity'
                  AND imj.status = 'failed'
                GROUP BY imj.fail_reason
                ORDER BY count DESC
            """)
            
            result = db.execute(failed_query)
            failed_reasons = result.fetchall()
        except Exception as e:
            print(f"   Error al obtener jobs fallidos: {e}")
            failed_reasons = []
        
        if failed_reasons:
            print("   Razones de fallo:")
            for row in failed_reasons:
                print(f"     {row.fail_reason:30}: {row.count:4} leads (avg {row.avg_attempts} intentos)")
        else:
            print("   No hay jobs fallidos registrados")
        
        # 5. Recomendaciones
        print("\n5. RECOMENDACIONES:")
        
        if has_phone_and_name > 0:
            print(f"   ✅ {has_phone_and_name} leads tienen teléfono Y nombre - matching debería funcionar")
            print("      → Verificar normalización de teléfono y nombres")
        
        if has_phone > has_phone_and_name:
            print(f"   ⚠️  {has_phone - has_phone_and_name} leads tienen teléfono pero NO nombre")
            print("      → Matching por teléfono solo (menor confianza)")
        
        if has_nothing > 0:
            print(f"   ❌ {has_nothing} leads NO tienen datos suficientes")
            print("      → Requieren datos adicionales o matching manual")
        
        if candidates_by_phone > 0:
            print(f"   ✅ Se encontraron candidatos en drivers_index")
            print("      → Verificar por qué el matching no los detecta")
            print("      → Revisar lógica de matching en MatchingEngine")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    analyze_no_identity_leads()
