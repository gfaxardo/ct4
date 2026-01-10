#!/usr/bin/env python3
"""
Script para documentar y ayudar a resolver conflictos de scout attribution
Identifica personas con múltiples scout_ids y genera reporte para revisión manual
"""
import sys
from pathlib import Path
from datetime import datetime
import json

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)
conn = engine.connect()

print("="*80)
print("RESOLUCIÓN DE CONFLICTOS: Scout Attribution")
print("="*80)
print(f"Fecha: {datetime.now().isoformat()}\n")

try:
    # Obtener todos los conflictos
    print("PASO 1: Identificando conflictos...")
    
    query_conflicts = text("""
        SELECT 
            person_key,
            distinct_scout_count,
            scout_ids,
            source_tables,
            first_attribution_date,
            last_attribution_date,
            first_created_at,
            last_created_at,
            total_records,
            conflict_details
        FROM ops.v_scout_attribution_conflicts
        ORDER BY distinct_scout_count DESC, total_records DESC
    """)
    
    result = conn.execute(query_conflicts)
    conflicts = result.fetchall()
    
    print(f"  Conflictos encontrados: {len(conflicts)}")
    
    if len(conflicts) == 0:
        print("\n  ✅ No hay conflictos detectados.")
        conn.close()
        sys.exit(0)
    
    # Obtener información adicional de cada conflicto
    print(f"\nPASO 2: Analizando {len(conflicts)} conflictos...")
    
    conflict_details = []
    
    for conflict in conflicts:
        person_key = conflict[0]
        distinct_scout_count = conflict[1]
        scout_ids = conflict[2]
        source_tables = conflict[3]
        first_attribution_date = conflict[4]
        last_attribution_date = conflict[5]
        total_records = conflict[8]
        conflict_details_json = conflict[9]
        
        # Obtener información de la persona
        query_person = text("""
            SELECT 
                ir.primary_full_name,
                ir.primary_phone,
                ir.primary_license,
                ir.created_at
            FROM canon.identity_registry ir
            WHERE ir.person_key = :person_key
        """)
        
        result_person = conn.execute(query_person, {'person_key': person_key})
        person_info = result_person.fetchone()
        
        # Obtener información de lead_ledger (si existe)
        query_ledger = text("""
            SELECT 
                attributed_scout_id,
                attribution_rule,
                confidence_level,
                updated_at
            FROM observational.lead_ledger
            WHERE person_key = :person_key
            LIMIT 1
        """)
        
        result_ledger = conn.execute(query_ledger, {'person_key': person_key})
        ledger_info = result_ledger.fetchone()
        
        # Obtener detalles de cada fuente
        sources_detail = []
        if conflict_details_json:
            for detail in conflict_details_json:
                sources_detail.append({
                    'scout_id': detail.get('scout_id'),
                    'source_table': detail.get('source_table'),
                    'source_pk': detail.get('source_pk'),
                    'attribution_date': str(detail.get('attribution_date')) if detail.get('attribution_date') else None,
                    'created_at': str(detail.get('created_at')) if detail.get('created_at') else None,
                    'priority': detail.get('priority')
                })
        
        conflict_details.append({
            'person_key': str(person_key),
            'person_name': person_info[0] if person_info else None,
            'person_phone': person_info[1] if person_info else None,
            'person_license': person_info[2] if person_info else None,
            'person_created_at': str(person_info[3]) if person_info and person_info[3] else None,
            'distinct_scout_count': distinct_scout_count,
            'scout_ids': scout_ids,
            'source_tables': source_tables,
            'first_attribution_date': str(first_attribution_date) if first_attribution_date else None,
            'last_attribution_date': str(last_attribution_date) if last_attribution_date else None,
            'total_records': total_records,
            'ledger_attributed_scout_id': ledger_info[0] if ledger_info else None,
            'ledger_attribution_rule': ledger_info[1] if ledger_info else None,
            'ledger_confidence_level': str(ledger_info[2]) if ledger_info and ledger_info[2] else None,
            'ledger_updated_at': str(ledger_info[3]) if ledger_info and ledger_info[3] else None,
            'sources_detail': sources_detail
        })
    
    # Generar reporte
    print(f"\nPASO 3: Generando reporte...")
    
    report_path = Path(__file__).parent / "sql" / "SCOUT_CONFLICTS_REPORT.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Reporte de Conflictos de Scout Attribution\n\n")
        f.write(f"**Fecha de generación**: {datetime.now().isoformat()}\n")
        f.write(f"**Total conflictos**: {len(conflicts)}\n\n")
        f.write("## Resumen Ejecutivo\n\n")
        f.write(f"Se detectaron {len(conflicts)} personas con múltiples scout_ids asignados.\n")
        f.write("Estos conflictos requieren revisión manual para determinar el scout_id correcto.\n\n")
        f.write("## Recomendaciones\n\n")
        f.write("1. **Priorizar por fecha**: Usar el scout_id de la atribución más antigua (primera fecha)\n")
        f.write("2. **Priorizar por fuente**: `lead_ledger` > `lead_events` > `scouting_daily` > `migrations`\n")
        f.write("3. **Revisar evidencia**: Verificar `evidence_json` en `lead_ledger` para contexto\n")
        f.write("4. **Actualizar manualmente**: Usar SQL para actualizar `lead_ledger.attributed_scout_id`\n\n")
        f.write("## Detalles de Conflictos\n\n")
        
        for idx, conflict in enumerate(conflict_details, 1):
            f.write(f"### Conflicto {idx}: {conflict['person_key']}\n\n")
            f.write(f"**Persona**:\n")
            f.write(f"- Nombre: {conflict['person_name'] or 'N/A'}\n")
            f.write(f"- Teléfono: {conflict['person_phone'] or 'N/A'}\n")
            f.write(f"- Licencia: {conflict['person_license'] or 'N/A'}\n")
            f.write(f"- Creada: {conflict['person_created_at'] or 'N/A'}\n\n")
            
            f.write(f"**Conflictos**:\n")
            f.write(f"- Scout IDs distintos: {conflict['distinct_scout_count']}\n")
            f.write(f"- Scout IDs: {conflict['scout_ids']}\n")
            f.write(f"- Fuentes: {conflict['source_tables']}\n")
            f.write(f"- Primera atribución: {conflict['first_attribution_date'] or 'N/A'}\n")
            f.write(f"- Última atribución: {conflict['last_attribution_date'] or 'N/A'}\n")
            f.write(f"- Total registros: {conflict['total_records']}\n\n")
            
            f.write(f"**Estado en lead_ledger**:\n")
            if conflict['ledger_attributed_scout_id']:
                f.write(f"- Scout ID actual: {conflict['ledger_attributed_scout_id']}\n")
                f.write(f"- Attribution rule: {conflict['ledger_attribution_rule'] or 'N/A'}\n")
                f.write(f"- Confidence level: {conflict['ledger_confidence_level'] or 'N/A'}\n")
            else:
                f.write("- ⚠️ **NO tiene attributed_scout_id en lead_ledger**\n")
            f.write("\n")
            
            f.write(f"**Detalles por fuente**:\n")
            for source in conflict['sources_detail']:
                f.write(f"- Scout ID: {source['scout_id']}, Fuente: {source['source_table']}, ")
                f.write(f"PK: {source['source_pk']}, Fecha: {source['attribution_date'] or 'N/A'}, ")
                f.write(f"Prioridad: {source['priority']}\n")
            f.write("\n")
            
            f.write(f"**SQL para resolver** (ejemplo - ajustar scout_id según decisión):\n")
            f.write("```sql\n")
            f.write(f"-- Revisar evidencia primero:\n")
            f.write(f"SELECT person_key, attributed_scout_id, attribution_rule, evidence_json\n")
            f.write(f"FROM observational.lead_ledger\n")
            f.write(f"WHERE person_key = '{conflict['person_key']}';\n\n")
            f.write(f"-- Actualizar (reemplazar X con el scout_id correcto):\n")
            f.write(f"UPDATE observational.lead_ledger\n")
            f.write(f"SET attributed_scout_id = X,  -- Reemplazar X con scout_id correcto\n")
            f.write(f"    attribution_rule = COALESCE(attribution_rule, 'RESOLVED_MANUAL_CONFLICT'),\n")
            f.write(f"    evidence_json = COALESCE(evidence_json, '{{}}'::JSONB) || jsonb_build_object(\n")
            f.write(f"        'conflict_resolution', true,\n")
            f.write(f"        'conflict_resolution_date', NOW(),\n")
            f.write(f"        'conflict_scout_ids', {conflict['scout_ids']},\n")
            f.write(f"        'resolved_scout_id', X  -- Reemplazar X\n")
            f.write(f"    ),\n")
            f.write(f"    updated_at = NOW()\n")
            f.write(f"WHERE person_key = '{conflict['person_key']}';\n")
            f.write("```\n\n")
            f.write("---\n\n")
    
    print(f"  Reporte guardado en: {report_path}")
    
    # Generar JSON para procesamiento programático
    json_path = Path(__file__).parent / "sql" / "SCOUT_CONFLICTS_REPORT.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(conflict_details, f, indent=2, ensure_ascii=False)
    
    print(f"  JSON guardado en: {json_path}")
    
    print("\n" + "="*80)
    print("ANÁLISIS DE CONFLICTOS COMPLETADO")
    print("="*80)
    print(f"\nPróximos pasos:")
    print(f"1. Revisar reporte: {report_path}")
    print(f"2. Decidir scout_id correcto para cada conflicto")
    print(f"3. Ejecutar SQL de resolución (incluido en el reporte)")
    print(f"4. Verificar que conflictos se resuelvan en vista v_scout_attribution_conflicts")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()

