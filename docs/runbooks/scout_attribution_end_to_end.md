# Runbook: Atribución de Scouts End-to-End

## Objetivo Final

Cerrar definitivamente el problema de atribución de scouts y dejar:
1. Scout canónico por persona (si existe evidencia)
2. 0% de scouting_daily fuera de identidad por bug
3. Propagación correcta a lead_ledger
4. Clasificación explícita de legacy/no pagables
5. Vista FINAL para liquidación diaria de scouts

**GARANTÍA**: Nada rompe claims ni pagos Yango. Todo queda auditable, versionado y explicable.

---

## Definiciones Canónicas

### "Scout satisfactorio"
Existe `observational.lead_ledger.attributed_scout_id` asociado a un `person_key` válido.

### Orden de Prioridad de Fuentes
1. `observational.lead_ledger.attributed_scout_id` (prioridad 1)
2. `observational.lead_events.scout_id` (incluye `payload_json->>'scout_id'`) (prioridad 2)
3. `public.module_ct_migrations.scout_id` (prioridad 3)
4. `public.module_ct_scouting_daily.scout_id` (prioridad 4)

### Regla de Oro
- Si hay **1 scout inequívoco** → se propaga
- Si hay **>1 scout** → CONFLICTO, no inventar

---

## Qué se Arregló

### FASE 1: Bug de Identidad (CRÍTICO)
**Problema**: `scouting_daily` tiene `scout_id`, pero 0% tiene `identity_links`, por lo tanto 0% tiene scout satisfactorio.

**Solución**: Script `backfill_identity_links_scouting_daily.py`
- Matching por: `driver_license`, `driver_phone` (últimos 9 dígitos)
- Crea `identity_link` SOLO si no existe
- Guarda evidencia: `source_table`, `source_pk`, `match_method`, `match_confidence`
- Output: `total / created / skipped / ambiguous`

### FASE 2: Propagación a Lead_Ledger (CATEGORÍA D)
**Problema**: Personas con `scout_id` en `lead_events` pero NO en `lead_ledger`.

**Solución**: SQL `backfill_lead_ledger_attributed_scout.sql`
- Solo actualiza si hay **EXACTAMENTE 1 scout_id** distinto en eventos
- Campos: `attribution_rule = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'`, `attribution_confidence = 'high'`, `attribution_source = 'lead_events'`
- Auditoría: `ops.lead_ledger_scout_backfill_audit`

### FASE 3: Eventos sin Scout (CATEGORÍA A)
**Problema**: `module_ct_cabinet_leads` sin `scout_id` mapeado.

**Solución**: Vista `ops.v_cabinet_leads_missing_scout_alerts`
- Investiga: `referral_link_id`, `recruiter_id`, `utm`, `payload_json`
- NO inventa scouts, solo alerta

### FASE 4: Vistas Canónicas
**Vistas creadas**:
1. `ops.v_scout_attribution_raw`: UNION ALL de TODAS las fuentes normalizadas
2. `ops.v_scout_attribution`: 1 fila por `person_key` con scout canónico
3. `ops.v_scout_attribution_conflicts`: `person_key` con >1 scout distinto
4. `ops.v_persons_without_scout_categorized`: Categorías A/C/D

### FASE 5: Vista Final para Pagos
**Vista**: `ops.v_scout_payment_base`
- Incluye: `person_key`, `driver_id`, `scout_id` canónico, `origin_tag`, `milestone_reached`, `milestone_date`, `eligible_7d`, `amount_payable`, `payment_status`, `block_reason`
- **NO paga**, solo declara verdad operativa

---

## Cómo Re-ejecutar

### Opción 1: Ejecución Automática End-to-End

```bash
cd backend
python scripts/execute_scout_attribution_end_to_end.py
```

Este script ejecuta en orden:
1. Diagnóstico inicial (métricas BEFORE)
2. Identity backfill scouting_daily
3. Lead_ledger backfill
4. Crear/actualizar vistas
5. Verificación final (métricas AFTER)

**Salida**: Métricas BEFORE/AFTER, % scouting_daily con identity, % scout satisfactorio global.

### Opción 2: Ejecución Manual por Fases

#### FASE 1: Identity Backfill
```bash
cd backend
python scripts/backfill_identity_links_scouting_daily.py
```

#### FASE 2: Lead_Ledger Backfill
```bash
cd backend/scripts/sql
psql -d <database> -f backfill_lead_ledger_attributed_scout.sql
```

#### FASE 4: Crear Vistas
```bash
cd backend/scripts/sql
psql -d <database> -f create_v_scout_attribution_raw.sql
psql -d <database> -f create_v_scout_attribution.sql
psql -d <database> -f create_v_scout_attribution_conflicts.sql
psql -d <database> -f create_v_persons_without_scout_categorized.sql
psql -d <database> -f create_v_cabinet_leads_missing_scout_alerts.sql
psql -d <database> -f create_v_scout_payment_base.sql
```

---

## Cómo Validar

### Validación 1: scouting_daily con Identity
```sql
SELECT 
    COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS total_with_scout,
    COUNT(*) FILTER (
        WHERE scout_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
                AND il.source_pk = sd.id::TEXT
        )
    ) AS with_identity
FROM public.module_ct_scouting_daily sd;
```

**Esperado**: `with_identity > 0%` de `total_with_scout`

### Validación 2: Scout Satisfactorio Global
```sql
SELECT 
    COUNT(DISTINCT ll.person_key) AS total_satisfactory
FROM observational.lead_ledger ll
WHERE ll.attributed_scout_id IS NOT NULL;
```

**Esperado**: `total_satisfactory > 0`

### Validación 3: Categoría D Reducida
```sql
SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized
WHERE category = 'D';
```

**Esperado**: Reducción drástica después de FASE 2

### Validación 4: Conflictos
```sql
SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts;
```

**Esperado**: No crecen sin razón (solo deberían aparecer casos legítimos)

### Validación 5: Vista de Pagos
```sql
SELECT 
    payment_status,
    COUNT(*) as count
FROM ops.v_scout_payment_base
GROUP BY payment_status;
```

**Esperado**: `ELIGIBLE` > 0, `BLOCKED` con `block_reason` explícito

---

## Cómo Auditar

### Auditoría 1: Identity Links Backfill
```sql
SELECT 
    source_table,
    match_rule,
    confidence_level,
    COUNT(*) as count
FROM canon.identity_links
WHERE source_table = 'module_ct_scouting_daily'
    AND linked_at >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY source_table, match_rule, confidence_level;
```

### Auditoría 2: Lead_Ledger Backfill
```sql
SELECT 
    backfill_method,
    attribution_rule_new,
    COUNT(*) as count
FROM ops.lead_ledger_scout_backfill_audit
WHERE backfill_timestamp >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY backfill_method, attribution_rule_new;
```

### Auditoría 3: Cambios en Lead_Ledger
```sql
SELECT 
    person_key,
    old_attributed_scout_id,
    new_attributed_scout_id,
    attribution_rule_new,
    backfill_timestamp
FROM ops.lead_ledger_scout_backfill_audit
WHERE backfill_timestamp >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY backfill_timestamp DESC;
```

---

## Qué NO Tocar

### ⚠️ NO Modificar Claims ni Pagos Yango
- Las vistas `ops.v_scout_payment_base` **NO ejecutan pagos**
- Los scripts **NO modifican** tablas de claims existentes
- Solo **declaran verdad operativa**, no ejecutan transacciones

### ⚠️ NO Inventar Scouts
- Si hay >1 scout distinto → CONFLICTO (revisar manualmente)
- Si no hay evidencia → NO asignar scout
- Usar `ops.v_scout_attribution_conflicts` para revisar conflictos

### ⚠️ NO Modificar Identity_Links Existentes
- Los scripts son **idempotentes** (solo crean si no existen)
- NO actualizan `identity_links` existentes
- Solo crean nuevos links para registros sin identidad

### ⚠️ NO Ejecutar en Producción sin Backup
- Siempre hacer backup antes de ejecutar scripts de backfill
- Revisar métricas BEFORE/AFTER
- Validar que no se rompieron claims/pagos

---

## Troubleshooting

### Problema: scouting_daily sigue sin identity
**Causa posible**: Datos faltantes (phone/license) o matching falla
**Solución**: Revisar `canon.identity_unmatched` con `source_table = 'module_ct_scouting_daily'`

### Problema: Categoría D no se reduce
**Causa posible**: Personas no tienen `lead_ledger` creado aún
**Solución**: Estas personas necesitan pasar por el pipeline normal de creación de `lead_ledger` primero

### Problema: Conflictos aumentan
**Causa posible**: Datos inconsistentes o múltiples scouts legítimos
**Solución**: Revisar `ops.v_scout_attribution_conflicts` y resolver manualmente

---

## Contacto

Para problemas o dudas:
1. Revisar logs de ejecución
2. Consultar tablas de auditoría
3. Verificar métricas BEFORE/AFTER
4. Consultar vistas de diagnóstico

---

**Última actualización**: {{ timestamp }}
