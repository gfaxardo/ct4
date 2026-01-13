# Resumen: Registros Sin Scout

## 📊 Situación Actual

- **Total personas:** 1,919
- **Con scout atribuido:** 353 (18.39%)
- **Sin scout atribuido:** 1,566 (81.61%)
- **Con scout en eventos:** 527
- **Sin scout en lead_ledger:** 165

## 🔍 Razones Principales

### 1. **module_ct_cabinet_leads NO tiene scout_id** ⚠️ PROBLEMA PRINCIPAL
- **446 eventos** de cabinet leads
- **0% con scout_id** (100% sin scout)
- **Razón:** Los eventos de cabinet leads no incluyen scout_id en la ingesta

### 2. **165 personas con lead_ledger pero sin scout**
- **Attribution rule "B":** 163 casos (confidence medium, sin scout)
- **Attribution rule "U":** 2 casos (confidence low, unassigned)
- **Razón:** El proceso de atribución no asignó scout aunque hay evidencia

### 3. **527 personas con scout en eventos pero no en ledger**
- **Razón:** El scout está en `lead_events` pero no se propagó a `lead_ledger`
- **Solución:** Re-ejecutar proceso de atribución

### 4. **1,566 personas sin lead_ledger**
- Muchas tienen `identity_links` pero no `lead_ledger`
- Pueden ser casos legacy o que no pasaron por atribución

## 📋 Próximos Pasos (Priorizados)

### ✅ PASO 1: Backfill desde module_ct_cabinet_leads (ALTA PRIORIDAD)
**Problema:** 446 eventos sin scout_id  
**Solución:** Buscar scout_id en tabla fuente y actualizar eventos

### ✅ PASO 2: Re-ejecutar atribución (ALTA PRIORIDAD)  
**Problema:** 527 personas tienen scout en eventos pero no en ledger  
**Solución:** Re-ejecutar proceso de atribución o ajustar reglas

### ✅ PASO 3: Resolver casos attribution_rule "B" (MEDIA PRIORIDAD)
**Problema:** 163 casos con confidence medium pero sin scout  
**Solución:** Revisar evidencia y ajustar umbrales

### ✅ PASO 4: Clasificar casos legacy (BAJA PRIORIDAD)
**Problema:** Personas sin eventos ni ledger  
**Solución:** Categorizar como legacy

## 📁 Archivos Creados

1. `backend/scripts/sql/analyze_missing_scout_attribution.sql` - Análisis completo
2. `backend/scripts/sql/categorize_persons_without_scout.sql` - Vista de categorización
3. `backend/scripts/get_detailed_missing_scout_analysis.py` - Script de análisis
4. `backend/scripts/sql/NEXT_STEPS_MISSING_SCOUT.md` - Plan de acción detallado
5. `backend/scripts/sql/RESUMEN_MISSING_SCOUT.md` - Este resumen





