#!/usr/bin/env python3
"""
Script de prueba para auditoría semanal de Cobranza 14d.
Ejecuta la vista ops.v_cabinet_14d_funnel_audit_weekly y muestra los resultados.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
import json

# Configuración de base de datos (ajustar según tu entorno)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

def main():
    """Ejecuta la auditoría semanal y muestra resultados."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("=" * 80)
        print("AUDITORÍA SEMANAL COBRANZA 14D - EMBUDO POR LEAD_DATE")
        print("=" * 80)
        print()
        
        # Query: últimas 8 semanas
        query = text("""
            SELECT 
                week_start,
                leads_total,
                leads_with_identity,
                leads_with_driver,
                drivers_with_trips_14d,
                reached_m1_14d,
                reached_m5_14d,
                reached_m25_14d,
                claims_expected_m1,
                claims_expected_m5,
                claims_expected_m25,
                claims_present_m1,
                claims_present_m5,
                claims_present_m25,
                claims_missing_m1,
                claims_missing_m5,
                claims_missing_m25,
                debt_expected_total,
                pct_with_identity,
                pct_with_driver,
                pct_with_trips_14d
            FROM ops.v_cabinet_14d_funnel_audit_weekly
            ORDER BY week_start DESC
            LIMIT 8
        """)
        
        result = session.execute(query)
        rows = result.fetchall()
        
        if not rows:
            print("⚠️  No se encontraron datos en la vista.")
            print("   Verifica que la vista ops.v_cabinet_14d_funnel_audit_weekly existe.")
            return
        
        print(f"📊 Resultados: {len(rows)} semanas")
        print()
        
        # Encabezados
        print(f"{'Semana':<12} {'Leads':<8} {'Id':<6} {'Drv':<6} {'Trips':<7} {'M1':<5} {'M5':<5} {'M25':<6} {'Claims M1':<12} {'Claims M5':<12} {'Claims M25':<13} {'Deuda':<12}")
        print("-" * 120)
        
        # Filas
        for row in rows:
            week_str = str(row.week_start) if row.week_start else "N/A"
            leads = row.leads_total or 0
            identity = row.leads_with_identity or 0
            driver = row.leads_with_driver or 0
            trips = row.drivers_with_trips_14d or 0
            m1 = row.reached_m1_14d or 0
            m5 = row.reached_m5_14d or 0
            m25 = row.reached_m25_14d or 0
            claims_m1_exp = row.claims_expected_m1 or 0
            claims_m1_pres = row.claims_present_m1 or 0
            claims_m5_exp = row.claims_expected_m5 or 0
            claims_m5_pres = row.claims_present_m5 or 0
            claims_m25_exp = row.claims_expected_m25 or 0
            claims_m25_pres = row.claims_present_m25 or 0
            debt = float(row.debt_expected_total or 0)
            
            # Formato de claims (expected/present)
            claims_m1_str = f"{claims_m1_exp}/{claims_m1_pres}"
            claims_m5_str = f"{claims_m5_exp}/{claims_m5_pres}"
            claims_m25_str = f"{claims_m25_exp}/{claims_m25_pres}"
            
            print(f"{week_str:<12} {leads:<8} {identity:<6} {driver:<6} {trips:<7} {m1:<5} {m5:<5} {m25:<6} {claims_m1_str:<12} {claims_m5_str:<12} {claims_m25_str:<13} {debt:<12.2f}")
        
        print()
        print("=" * 80)
        print("ANÁLISIS DE GAPS")
        print("=" * 80)
        print()
        
        # Identificar semanas con problemas
        issues = []
        for row in rows:
            week_str = str(row.week_start) if row.week_start else "N/A"
            issues_week = []
            
            # C1: leads_total post-05 = 0
            if row.leads_total == 0:
                issues_week.append("❌ C1: No hay leads en esta semana")
            
            # C2: leads_total > 0 pero leads_with_identity ~ 0
            if row.leads_total > 0 and row.leads_with_identity == 0:
                issues_week.append(f"❌ C2: {row.leads_total} leads sin identity (0% match)")
            elif row.leads_total > 0 and row.pct_with_identity < 50:
                issues_week.append(f"⚠️  C2: Solo {row.pct_with_identity:.1f}% con identity")
            
            # C3: identity ok pero driver ok = 0
            if row.leads_with_identity > 0 and row.leads_with_driver == 0:
                issues_week.append(f"❌ C3: {row.leads_with_identity} leads con identity pero sin driver_id")
            elif row.leads_with_identity > 0 and row.pct_with_driver < 50:
                issues_week.append(f"⚠️  C3: Solo {row.pct_with_driver:.1f}% con driver_id")
            
            # C4: driver ok pero milestones 14d = 0
            if row.leads_with_driver > 0 and row.drivers_with_trips_14d == 0:
                issues_week.append(f"❌ C4: {row.leads_with_driver} drivers sin trips en 14d")
            elif row.leads_with_driver > 0 and row.pct_with_trips_14d < 50:
                issues_week.append(f"⚠️  C4: Solo {row.pct_with_trips_14d:.1f}% con trips 14d")
            
            # C5: milestones ok pero claims_present = 0
            if row.reached_m1_14d > 0 and row.claims_present_m1 == 0:
                issues_week.append(f"❌ C5: {row.reached_m1_14d} drivers alcanzaron M1 pero 0 claims M1")
            if row.reached_m5_14d > 0 and row.claims_present_m5 == 0:
                issues_week.append(f"❌ C5: {row.reached_m5_14d} drivers alcanzaron M5 pero 0 claims M5")
            if row.reached_m25_14d > 0 and row.claims_present_m25 == 0:
                issues_week.append(f"❌ C5: {row.reached_m25_14d} drivers alcanzaron M25 pero 0 claims M25")
            
            # Gaps de claims
            if row.claims_missing_m1 > 0:
                issues_week.append(f"⚠️  Claims M1 faltantes: {row.claims_missing_m1}")
            if row.claims_missing_m5 > 0:
                issues_week.append(f"⚠️  Claims M5 faltantes: {row.claims_missing_m5}")
            if row.claims_missing_m25 > 0:
                issues_week.append(f"⚠️  Claims M25 faltantes: {row.claims_missing_m25}")
            
            if issues_week:
                issues.append((week_str, issues_week))
        
        if issues:
            for week_str, week_issues in issues:
                print(f"📅 Semana {week_str}:")
                for issue in week_issues:
                    print(f"   {issue}")
                print()
        else:
            print("✅ No se encontraron problemas críticos en las últimas 8 semanas.")
        
        print()
        print("=" * 80)
        print("QUERY DE PRUEBA: Leads post-05/01/2026")
        print("=" * 80)
        print()
        
        # Query específica para leads post-05
        query_post_05 = text("""
            SELECT 
                COUNT(*) AS total_leads,
                COUNT(DISTINCT COALESCE(external_id::text, id::text)) AS distinct_pk,
                MIN(lead_created_at::date) AS min_date,
                MAX(lead_created_at::date) AS max_date
            FROM public.module_ct_cabinet_leads
            WHERE lead_created_at::date > '2026-01-05'
        """)
        
        result_post_05 = session.execute(query_post_05)
        row_post_05 = result_post_05.fetchone()
        
        if row_post_05 and row_post_05.total_leads > 0:
            print(f"✅ Encontrados {row_post_05.total_leads} leads post-05/01/2026")
            print(f"   Rango: {row_post_05.min_date} a {row_post_05.max_date}")
            print()
            print("   Verifica si estos leads aparecen en la auditoría semanal arriba.")
        else:
            print("⚠️  No se encontraron leads post-05/01/2026 en module_ct_cabinet_leads")
            print("   Esto sugiere que el problema está en la fuente de datos RAW.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
