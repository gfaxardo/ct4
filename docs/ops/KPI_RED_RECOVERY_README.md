# KPI Red Recovery - Módulo de Drenaje del Backlog

## 📋 PROPÓSITO

Este módulo está diseñado para **drenar específicamente el backlog del KPI rojo** ("Leads sin identidad ni claims"), procesando PRIORITARIAMENTE los leads que el KPI rojo cuenta como "sin identidad ni claims".

## ⚠️ DIFERENCIAS CRÍTICAS

### "Matched last 24h" ≠ "Drenado del KPI rojo"

**IMPORTANTE:** El módulo "Matched last 24h" (`ops.identity_matching_jobs`) y el módulo "KPI Red Recovery" (`ops.cabinet_kpi_red_recovery_queue`) son **DIFERENTES**:

- **"Matched last 24h"**: Cuenta TODOS los matches de identidad en las últimas 24 horas, independientemente de si estaban en el KPI rojo o no.
- **"KPI Red Recovery"**: Procesa ESPECÍFICAMENTE los leads que están en el KPI rojo y los drena del backlog.

**El único KPI de éxito del recovery dirigido es:**
- `matched_out > new_backlog_in` (más leads recuperados que nuevos leads entrando)
- Y/O `backlog_end < backlog_start` (backlog disminuye)

## 🎯 CRITERIOS DE ÉXITO

### Éxito del Recovery Dirigido

El sistema tiene éxito cuando:
1. **Backlog disminuye**: `backlog_end < backlog_start`
2. **Throughput positivo**: `matched_out > new_backlog_in`
3. **Leads matched NO están en backlog**: 0% de leads matched aparecen en `ops.v_cabinet_kpi_red_backlog`

### Si el KPI rojo NO baja

**El sistema NO está fallando.** El sistema está explicando por qué no puede bajar:

1. **Falta de datos**: `fail_reason = 'missing_identifiers'` o `'no_match_found'`
   - Los leads no tienen phone/doc/email suficientes para matching
   - **Solución**: Mejorar calidad de datos en origen

2. **Conflictos**: `fail_reason = 'conflict_multiple_candidates'`
   - Se encontraron múltiples candidatos con scores muy cercanos
   - **Solución**: Revisión manual o ajustar reglas de matching

3. **Backlog entrante mayor**: `new_backlog_in > matched_out`
   - Entran más leads nuevos al backlog de los que se recuperan
   - **Solución**: Aumentar frecuencia del job o capacidad de procesamiento

## 🏗️ ARQUITECTURA

### Componentes

1. **Vista de Backlog**: `ops.v_cabinet_kpi_red_backlog`
   - Define el set exacto de leads en el KPI rojo
   - Source of truth para el backlog

2. **Tabla de Cola**: `ops.cabinet_kpi_red_recovery_queue`
   - Cola de trabajo para procesar leads del backlog
   - Estados: `pending`, `matched`, `failed`

3. **Job Seed**: `backend/jobs/seed_kpi_red_queue.py`
   - Sembrar la cola desde el backlog
   - Ejecutar cada hora/día

4. **Job Recovery**: `backend/jobs/recover_kpi_red_leads.py`
   - Procesar leads pending de la cola
   - Intentar matching y crear links/origin
   - Ejecutar cada 1-4 horas

5. **Vista de Métricas**: `ops.v_cabinet_kpi_red_recovery_metrics_daily`
   - Métricas diarias de recovery
   - Backlog, throughput, net change

6. **Endpoint**: `GET /api/v1/ops/payments/cabinet-financial-14d/kpi-red-recovery-metrics`
   - Exponer métricas de recovery

## 🔧 CONSISTENCIA DE source_pk

**CRÍTICO:** Todos los `source_pk` usan el mismo formato:

```sql
COALESCE(external_id::text, id::text)
```

Este formato se usa en:
- `ops.v_cabinet_kpi_red_backlog.lead_source_pk`
- `ops.cabinet_kpi_red_recovery_queue.lead_source_pk`
- `canon.identity_links.source_pk` (cuando `source_table = 'module_ct_cabinet_leads'`)

**Verificación:** Ejecutar `backend/scripts/verify_source_pk_consistency.py`

## 🔒 GUARDRAIL

### Verificación Automática

Ejecutar periódicamente:
```bash
python -m scripts.verify_kpi_red_drain
```

Este script verifica que:
- 0% de leads matched (`status='matched'` en queue) aparecen en el backlog
- Si algún lead matched está en el backlog → `exit(1)` (fallo crítico)

**Causas comunes de fallo:**
1. `source_pk` mismatch (casting diferente)
2. `identity_link` no se creó correctamente
3. Vista del backlog no sincronizada
4. Race condition (lead matched después de snapshot)

## 📊 MÉTRICAS

### Métricas Diarias

- **backlog_start**: Backlog al inicio del día
- **new_backlog_in**: Leads que entraron al backlog en este día
- **matched_out**: Leads que fueron matched (salieron del backlog) en este día
- **backlog_end**: Backlog al final del día (`backlog_start + new_backlog_in - matched_out`)
- **net_change**: Cambio neto (`new_backlog_in - matched_out`)
- **top_fail_reason**: Razón de fallo más común

### Interpretación

- **net_change > 0**: Entran más leads de los que se recuperan (backlog crece)
- **net_change < 0**: Se recuperan más leads de los que entran (backlog disminuye)
- **net_change = 0**: Balance (backlog estable)

## 🚀 EJECUCIÓN

### Primera Vez

1. **Ejecutar migración:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Crear vistas SQL:**
   ```bash
   psql -d <database> -f backend/sql/ops/v_cabinet_kpi_red_backlog.sql
   psql -d <database> -f backend/sql/ops/v_cabinet_kpi_red_recovery_metrics_daily.sql
   ```

3. **Sembrar cola (primera vez):**
   ```bash
   python -m jobs.seed_kpi_red_queue
   ```

4. **Ejecutar recovery:**
   ```bash
   python -m jobs.recover_kpi_red_leads --limit 1000
   ```

### Operación Continua

- **Job Seed**: Ejecutar cada hora/día (mantener cola sincronizada con backlog)
- **Job Recovery**: Ejecutar cada 1-4 horas (drenar backlog)
- **Guardrail**: Ejecutar periódicamente para verificar integridad

## ✅ VALIDACIÓN

### Validación de Impacto Real

Ejecutar:
```bash
python -m scripts.validate_kpi_red_impact --limit 1000
```

Este script:
1. Obtiene backlog ANTES
2. Ejecuta seed
3. Ejecuta recovery
4. Obtiene backlog DESPUÉS
5. Reporta diferencia y razones de fallo

### Verificaciones de Producción

Antes de mergear, ejecutar:

1. **Alembic heads:**
   ```bash
   alembic heads
   ```
   Debe retornar 1 solo head

2. **Consistencia source_pk:**
   ```bash
   python -m scripts.verify_source_pk_consistency
   ```

3. **Identity origin creation:**
   ```bash
   python -m scripts.verify_identity_origin_creation
   ```

4. **Guardrail:**
   ```bash
   python -m scripts.verify_kpi_red_drain
   ```

## 📝 NOTAS

- El sistema es **idempotente**: puede ejecutarse múltiples veces sin romper
- Los jobs procesan en **batches** (500-1000 leads por batch)
- El job seed puede ejecutarse frecuentemente sin problemas (upsert idempotente)
- El job recovery debe ejecutarse periódicamente para drenar el backlog
- **ORIGIN_MISSING se corrige automáticamente**: cuando hay link, se crea origin
