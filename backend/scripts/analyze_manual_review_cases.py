"""
Script para analizar las 902 personas que requieren revisión manual.
Genera un reporte detallado con recomendaciones.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.db import SessionLocal
from app.models.canon import IdentityRegistry, IdentityLink
from datetime import datetime
import json

def analyze_manual_review_cases():
    """
    Analiza las personas que requieren revisión manual y genera recomendaciones.
    """
    db = SessionLocal()
    
    try:
        # Obtener personas sin origen determinado
        query = text("""
            SELECT DISTINCT ir.person_key, ir.created_at
            FROM canon.identity_registry ir
            WHERE NOT EXISTS (
                SELECT 1 FROM canon.identity_origin io 
                WHERE io.person_key = ir.person_key
            )
            ORDER BY ir.created_at
        """)
        
        persons = db.execute(query).fetchall()
        
        print(f"\n{'='*80}")
        print(f"ANALISIS DE CASOS QUE REQUIEREN REVISION MANUAL")
        print(f"{'='*80}\n")
        print(f"Total de personas sin origen: {len(persons)}\n")
        
        # Analizar por tipo de link
        analysis = {
            "solo_drivers": [],
            "sin_links": [],
            "con_lead_links_sin_driver": [],
            "con_multiple_lead_types": [],
            "otros": []
        }
        
        for person_row in persons:
            person_key = person_row.person_key
            
            # Obtener todos los links
            links_query = text("""
                SELECT source_table, source_pk, match_rule, linked_at, match_score, confidence_level
                FROM canon.identity_links
                WHERE person_key = :person_key
                ORDER BY linked_at
            """)
            
            links = db.execute(links_query, {"person_key": str(person_key)}).fetchall()
            
            link_tables = [link.source_table for link in links]
            lead_tables = ["module_ct_cabinet_leads", "module_ct_scouting_daily", "module_ct_migrations"]
            has_driver = "drivers" in link_tables
            has_leads = any(table in link_tables for table in lead_tables)
            
            person_info = {
                "person_key": str(person_key),
                "created_at": person_row.created_at.isoformat() if person_row.created_at else None,
                "links": [
                    {
                        "source_table": link.source_table,
                        "source_pk": link.source_pk,
                        "match_rule": link.match_rule,
                        "linked_at": link.linked_at.isoformat() if link.linked_at else None,
                        "match_score": link.match_score,
                        "confidence_level": link.confidence_level.value if hasattr(link.confidence_level, 'value') else str(link.confidence_level)
                    }
                    for link in links
                ],
                "total_links": len(links)
            }
            
            # Clasificar
            if not links:
                analysis["sin_links"].append(person_info)
            elif has_driver and not has_leads:
                analysis["solo_drivers"].append(person_info)
            elif has_leads and not has_driver:
                analysis["con_lead_links_sin_driver"].append(person_info)
            elif len([t for t in link_tables if t in lead_tables]) > 1:
                analysis["con_multiple_lead_types"].append(person_info)
            else:
                analysis["otros"].append(person_info)
        
        # Reporte por categoría
        print(f"CATEGORIZACION:\n")
        print(f"  - Solo drivers (sin leads): {len(analysis['solo_drivers'])}")
        print(f"  - Sin links: {len(analysis['sin_links'])}")
        print(f"  - Con leads pero sin driver: {len(analysis['con_lead_links_sin_driver'])}")
        print(f"  - Con múltiples tipos de leads: {len(analysis['con_multiple_lead_types'])}")
        print(f"  - Otros casos: {len(analysis['otros'])}\n")
        
        # Análisis detallado de "solo_drivers"
        if analysis["solo_drivers"]:
            print(f"{'='*80}")
            print(f"CASOS: SOLO DRIVERS (SIN LEADS) - {len(analysis['solo_drivers'])} personas")
            print(f"{'='*80}\n")
            
            # Analizar por match_rule
            match_rules = {}
            for person in analysis["solo_drivers"][:10]:  # Primeros 10
                for link in person["links"]:
                    if link["source_table"] == "drivers":
                        rule = link["match_rule"]
                        if rule not in match_rules:
                            match_rules[rule] = []
                        match_rules[rule].append(person["person_key"])
            
            print(f"Distribución por match_rule (primeros 10 casos):")
            for rule, person_keys in match_rules.items():
                print(f"  - {rule}: {len(person_keys)} casos")
            
            print(f"\nMuestra de casos (primeros 5):")
            for i, person in enumerate(analysis["solo_drivers"][:5], 1):
                print(f"\n  {i}. Person Key: {person['person_key']}")
                print(f"     Created At: {person['created_at']}")
                print(f"     Links:")
                for link in person["links"]:
                    print(f"       - {link['source_table']}: {link['source_pk']} (rule: {link['match_rule']}, score: {link['match_score']})")
        
        # Análisis de "sin_links"
        if analysis["sin_links"]:
            print(f"\n{'='*80}")
            print(f"CASOS: SIN LINKS - {len(analysis['sin_links'])} personas")
            print(f"{'='*80}\n")
            print(f"Estas personas no tienen ningún link asociado.")
            print(f"Recomendación: Investigar por qué fueron creadas sin links.\n")
        
        # Análisis de "con_lead_links_sin_driver"
        if analysis["con_lead_links_sin_driver"]:
            print(f"\n{'='*80}")
            print(f"CASOS: CON LEADS PERO SIN DRIVER - {len(analysis['con_lead_links_sin_driver'])} personas")
            print(f"{'='*80}\n")
            print(f"Estas personas tienen leads pero nunca se creó el link de driver.")
            print(f"Recomendación: Verificar si el driver existe y crear el link faltante.\n")
        
        # Generar recomendaciones
        print(f"\n{'='*80}")
        print(f"RECOMENDACIONES")
        print(f"{'='*80}\n")
        
        recommendations = []
        
        if len(analysis["solo_drivers"]) > 0:
            recommendations.append({
                "categoria": "Solo Drivers",
                "cantidad": len(analysis["solo_drivers"]),
                "accion": "mark_legacy",
                "descripcion": "Marcar como legacy_external si first_seen_at < LEAD_SYSTEM_START_DATE",
                "prioridad": "alta" if len(analysis["solo_drivers"]) > 100 else "media"
            })
        
        if len(analysis["sin_links"]) > 0:
            recommendations.append({
                "categoria": "Sin Links",
                "cantidad": len(analysis["sin_links"]),
                "accion": "investigar",
                "descripcion": "Investigar por qué fueron creadas sin links. Posiblemente datos corruptos o proceso incompleto.",
                "prioridad": "alta"
            })
        
        if len(analysis["con_lead_links_sin_driver"]) > 0:
            recommendations.append({
                "categoria": "Leads sin Driver",
                "cantidad": len(analysis["con_lead_links_sin_driver"]),
                "accion": "auto_link",
                "descripcion": "Intentar crear links de driver mediante matching. Si no existe driver, puede ser lead que nunca se convirtió (normal).",
                "prioridad": "media"
            })
        
        if len(analysis["con_multiple_lead_types"]) > 0:
            recommendations.append({
                "categoria": "Múltiples Tipos de Leads",
                "cantidad": len(analysis["con_multiple_lead_types"]),
                "accion": "manual_review",
                "descripcion": "Aplicar reglas de prioridad: cabinet > scout > migration",
                "prioridad": "media"
            })
        
        for rec in recommendations:
            print(f"  [{rec['prioridad'].upper()}] {rec['categoria']}: {rec['cantidad']} casos")
            print(f"      Acción: {rec['accion']}")
            print(f"      Descripción: {rec['descripcion']}\n")
        
        # Guardar análisis en JSON
        output_file = project_root / "scripts" / "manual_review_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total": len(persons),
                "categorias": {k: len(v) for k, v in analysis.items()},
                "recomendaciones": recommendations,
                "muestras": {
                    "solo_drivers": analysis["solo_drivers"][:10],
                    "sin_links": analysis["sin_links"][:5],
                    "con_lead_links_sin_driver": analysis["con_lead_links_sin_driver"][:5]
                }
            }, f, indent=2, default=str)
        
        print(f"\nAnálisis guardado en: {output_file}\n")
        
        return analysis, recommendations
    
    except Exception as e:
        print(f"Error en análisis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    analyze_manual_review_cases()

