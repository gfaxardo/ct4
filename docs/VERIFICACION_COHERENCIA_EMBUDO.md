# Verificación de Coherencia del Embudo de Cobranza Yango

## ✅ Verificación Completa: Base del Embudo = module_ct_cabinet_leads

### Flujo Verificado

```
✅ 1. BASE: module_ct_cabinet_leads
   └─ Todos los leads registrados desde Yango
   └─ Fuente única de verdad para métricas

✅ 2. INGESTA: process_cabinet_leads()
   └─ Lee de: module_ct_cabinet_leads
   └─ Crea: identity_links (si hay match) o identity_unmatched (si no hay match)
   └─ GAP 1: Leads sin identity_links → NO continúan

✅ 3. ATRIBUCIÓN: populate_events_from_cabinet()
   └─ Lee de: module_ct_cabinet_leads
   └─ Busca: identity_links para obtener person_key
   └─ Crea: lead_events (puede tener person_key = NULL si no hay identity_links)
   └─ GAP 1: lead_events con person_key = NULL → NO continúan

✅ 4. CONVERSIÓN: v_conversion_metrics
   └─ Filtra: WHERE person_key IS NOT NULL
   └─ Resuelve: driver_id desde identity_links (source_table = 'drivers')
   └─ Calcula: viajes en ventana de 14 días
   └─ GAP 2: Leads sin driver_id → NO generan claims

✅ 5. CÁLCULO: v_payment_calculation
   └─ Filtra: WHERE driver_id IS NOT NULL
   └─ Genera: claims por milestone alcanzado
   └─ GAP 3: Leads sin milestones → NO generan claims

✅ 6. CLAIMS: v_claims_payment_status_cabinet
   └─ Agrega: claims por (driver_id, milestone_value)
   └─ Reconcilia: con pagos de Yango
   └─ GAP 4: Claims sin pagos → Deuda pendiente

✅ 7. FINANCIERA: v_cabinet_financial_14d
   └─ Usa: v_conversion_metrics (requiere person_key IS NOT NULL)
   └─ Usa: v_payment_calculation (requiere driver_id IS NOT NULL)
   └─ SOLO muestra: leads con identidad Y driver_id
   └─ NO incluye: leads sin identity_links (GAP 1)
```

### Coherencia Verificada

#### ✅ Base del Embudo
- **Todas las métricas parten de `module_ct_cabinet_leads`**
- El endpoint `/funnel-gap` cuenta desde `module_ct_cabinet_leads`
- La vista `v_leads_without_identity_or_payment` parte de `module_ct_cabinet_leads`
- El resumen ejecutivo identifica `module_ct_cabinet_leads` como base

#### ✅ Proceso de Ingesta
- `process_cabinet_leads()` lee de `module_ct_cabinet_leads`
- Crea `identity_links` si hay match
- Crea `identity_unmatched` si no hay match
- **GAP 1**: Leads sin `identity_links` → NO continúan

#### ✅ Proceso de Atribución
- `populate_events_from_cabinet()` lee de `module_ct_cabinet_leads`
- Busca `identity_links` para obtener `person_key`
- Crea `lead_events` (puede tener `person_key = NULL`)
- **GAP 1**: `lead_events` con `person_key = NULL` → NO continúan

#### ✅ Vista de Conversión
- `v_conversion_metrics` filtra `WHERE person_key IS NOT NULL`
- Solo incluye `lead_events` con identidad válida
- Resuelve `driver_id` desde `identity_links` (source_table = 'drivers')
- **GAP 2**: Leads sin `driver_id` → NO generan claims

#### ✅ Vista de Cálculo de Pagos
- `v_payment_calculation` filtra `WHERE driver_id IS NOT NULL`
- Solo incluye leads con `driver_id` válido
- Genera claims por milestone alcanzado
- **GAP 3**: Leads sin milestones → NO generan claims

#### ✅ Vista de Claims
- `v_claims_payment_status_cabinet` usa `v_payment_calculation`
- Solo incluye claims de leads con `driver_id` y milestones
- Reconcilia con pagos de Yango
- **GAP 4**: Claims sin pagos → Deuda pendiente

#### ✅ Vista Financiera
- `v_cabinet_financial_14d` usa `v_conversion_metrics` y `v_payment_calculation`
- Solo muestra leads que pasaron ambos filtros (identidad + driver_id)
- **NO incluye**: Leads sin `identity_links` (GAP 1)

### Métricas del Gap Verificadas

#### ✅ Endpoint `/funnel-gap`
- Cuenta desde `module_ct_cabinet_leads` (BASE)
- Verifica `identity_links` (GAP 1)
- Verifica claims (GAP 1, 2, 3)
- Calcula porcentajes correctamente

#### ✅ Vista `v_leads_without_identity_or_payment`
- Parte de `module_ct_cabinet_leads` (BASE)
- Identifica leads sin `identity_links` (GAP 1)
- Identifica leads sin claims (GAP 1, 2, 3)
- Incluye razón del gap

### Resumen Ejecutivo Verificado

#### ✅ Flujo de Datos
- Identifica `module_ct_cabinet_leads` como base del embudo
- Explica cada paso del flujo correctamente
- Identifica los gaps en cada etapa
- Explica por qué leads sin identidad NO aparecen en vista financiera

#### ✅ Métricas del Gap
- Define correctamente el GAP 1 (sin identidad ni claims)
- Explica el impacto (leads invisibles para cobranza)
- Proporciona queries SQL correctas
- Incluye interpretación y acciones recomendadas

### Conclusión

✅ **TODO ESTÁ COHERENTE**

El sistema está correctamente alineado:
1. **Base del embudo**: `module_ct_cabinet_leads` es la fuente única de verdad
2. **Proceso de ingesta**: Crea `identity_links` o `identity_unmatched` correctamente
3. **Filtros en cascada**: Cada vista filtra correctamente (person_key, driver_id, milestones)
4. **Vista financiera**: Solo muestra leads que pasaron todos los filtros
5. **Métricas del gap**: Miden correctamente desde la base del embudo
6. **Resumen ejecutivo**: Refleja correctamente todo el flujo

**Última verificación**: Enero 2026

