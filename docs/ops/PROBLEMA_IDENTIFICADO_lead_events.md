# 🔍 Problema Identificado: lead_events no se actualiza

## Problema Raíz

**El proceso de ingesta de identidad (`IngestionService`) NO crea eventos en `lead_events`.**

Hay DOS procesos separados:

1. **`IngestionService`** (`/api/v1/identity/run`)
   - ✅ Crea `identity_links` (vincula personas con fuentes RAW)
   - ❌ NO crea eventos en `lead_events`

2. **`LeadAttributionService`** (`/api/v1/attribution/populate-events`)
   - ✅ Crea eventos en `lead_events` desde tablas fuente
   - ❌ NO está automatizado

## Consecuencia

- La ingesta de identidad se ejecuta automáticamente cada 6 horas
- Pero `lead_events` NO se actualiza porque `populate_events` no se ejecuta
- Por lo tanto, `v_conversion_metrics` no tiene nuevos `lead_date`
- Y `v_cabinet_financial_14d` sigue mostrando solo hasta el 14/12

## Solución Implementada

### 1. Script Actualizado

**Archivo:** `backend/scripts/run_identity_ingestion_scheduled.py`

**Cambio:** Ahora ejecuta AMBOS procesos:
1. `IngestionService.run_ingestion()` - Crea `identity_links`
2. `LeadAttributionService.populate_events_from_scouting()` - Crea `lead_events`

### 2. Script Alternativo

**Archivo:** `backend/scripts/run_populate_events_via_api.py`

**Uso:** Para ejecutar solo `populate_events` vía API

## Acción Requerida

### Opción 1: Ejecutar populate_events Manualmente (Inmediato)

```bash
# Vía API (si el servidor está corriendo)
python backend/scripts/run_populate_events_via_api.py

# O directamente vía curl
curl -X POST "http://localhost:8000/api/v1/attribution/populate-events" \
  -H "Content-Type: application/json" \
  -d '{"source_tables": ["module_ct_scouting_daily"], "date_from": "2025-12-15", "date_to": "2026-01-07"}'
```

### Opción 2: Actualizar Task Scheduler

El script `run_identity_ingestion_scheduled.py` ahora ejecuta ambos procesos. La próxima vez que se ejecute automáticamente (en 6 horas), poblará `lead_events`.

O ejecutar manualmente ahora:
```bash
# Activar entorno virtual primero
cd C:\cursor\CT4\backend
.\venv\Scripts\Activate.ps1
python scripts/run_identity_ingestion_scheduled.py
```

## Verificación

Después de ejecutar `populate_events`:

```sql
-- Verificar que lead_events se actualizó
SELECT MAX(event_date) FROM observational.lead_events;

-- Verificar que v_conversion_metrics se actualizó
SELECT MAX(lead_date) FROM observational.v_conversion_metrics 
WHERE origin_tag = 'cabinet';

-- Verificar que v_cabinet_financial_14d se actualizó
SELECT MAX(lead_date) FROM ops.v_cabinet_financial_14d;
```

## Nota Importante

El proceso de `populate_events` requiere que existan `identity_links` primero. Por eso el script actualizado ejecuta:
1. Primero: `run_ingestion()` - Crea `identity_links`
2. Segundo: `populate_events_from_scouting()` - Crea `lead_events` usando los `identity_links`

