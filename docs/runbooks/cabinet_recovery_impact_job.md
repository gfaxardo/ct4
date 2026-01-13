# Runbook: Cabinet Recovery Impact Job

## Propósito

Job permanente que conecta Recovery (Brechas de Identidad) con impacto en Cobranza Cabinet 14d.

**Objetivo:** Asegurar que cuando el matching engine encuentre person_key para un lead cabinet, se crea/actualiza el vínculo canónico y se registra en audit para medición de impacto.

---

## Funcionalidad

El job procesa leads "unidentified" o "identified_no_origin" en `ops.v_cabinet_identity_recovery_impact_14d` y:

1. **Asegura identity_origin:** Crea/actualiza `canon.identity_origin` con `origin_tag='cabinet_lead'` y `origin_source_id=lead_id`
2. **Registra en audit:** Crea/actualiza `ops.cabinet_lead_recovery_audit` con `first_recovered_at` y `last_recovered_at`

**IMPORTANTE:**
- Solo procesa leads que YA tienen `person_key_effective` (necesita matching primero)
- Es idempotente: puede ejecutarse múltiples veces sin romper
- No destructivo: solo crea/actualiza, nunca elimina

---

## Ejecución Manual

### Opción 1: Python Directo

```bash
cd backend
python -m jobs.cabinet_recovery_impact_job
```

### Opción 2: Con Límite

```bash
cd backend
python -m jobs.cabinet_recovery_impact_job 1000
```

### Opción 3: Desde Python

```python
from jobs.cabinet_recovery_impact_job import run_job

result = run_job(limit=1000)
print(result)
```

---

## Programación (Cron)

### Ejecutar cada 1 hora

```cron
0 * * * * cd /path/to/backend && python -m jobs.cabinet_recovery_impact_job >> /var/log/cabinet_recovery_impact_job.log 2>&1
```

### Ejecutar cada 4 horas

```cron
0 */4 * * * cd /path/to/backend && python -m jobs.cabinet_recovery_impact_job >> /var/log/cabinet_recovery_impact_job.log 2>&1
```

### Ejecutar diariamente a las 2:00 AM

```cron
0 2 * * * cd /path/to/backend && python -m jobs.cabinet_recovery_impact_job >> /var/log/cabinet_recovery_impact_job.log 2>&1
```

---

## Parámetros

- `limit` (opcional): Número máximo de leads a procesar. Si no se especifica, procesa hasta 10000.

---

## Estadísticas de Salida

El job retorna un diccionario con:

```python
{
    "processed": int,        # Total procesados
    "links_created": int,    # Links creados (si aplica)
    "links_updated": int,    # Links actualizados (si aplica)
    "origins_created": int,  # Origins creados
    "origins_updated": int,  # Origins actualizados
    "audit_created": int,    # Registros de audit creados
    "audit_updated": int,    # Registros de audit actualizados
    "skipped": int,          # Leads omitidos (sin person_key)
    "errors": list           # Lista de errores (si hay)
}
```

---

## Verificación

### Verificar que el job está funcionando

```sql
-- Ver registros recientes en audit
SELECT 
    lead_id,
    first_recovered_at,
    last_recovered_at,
    recovered_person_key,
    recovery_method
FROM ops.cabinet_lead_recovery_audit
ORDER BY first_recovered_at DESC
LIMIT 10;
```

### Verificar impactos

```sql
-- Ver leads recuperados
SELECT 
    impact_bucket,
    COUNT(*) as count
FROM ops.v_cabinet_identity_recovery_impact_14d
GROUP BY impact_bucket
ORDER BY count DESC;
```

---

## Troubleshooting

### Error: "Table ops.cabinet_lead_recovery_audit does not exist"

**Solución:** Ejecutar la migración:

```bash
cd backend
alembic upgrade head
```

### Error: "View ops.v_cabinet_identity_recovery_impact_14d does not exist"

**Solución:** Crear las vistas SQL primero:

```bash
psql -d yego_integral -f backend/sql/ops/v_cabinet_lead_identity_effective.sql
psql -d yego_integral -f backend/sql/ops/v_cabinet_identity_recovery_impact_14d.sql
```

### El job no procesa ningún lead

**Verificar:**
1. ¿Hay leads en `ops.v_cabinet_identity_recovery_impact_14d` con `claim_status_bucket IN ('unidentified', 'identified_no_origin')`?
2. ¿Esos leads tienen `person_key_effective`? (El job solo procesa leads que ya tienen person_key)

---

## Logs

El job registra logs en el logger `jobs.cabinet_recovery_impact_job`.

Configurar logging en `backend/app/logging_config.py` o usar logging estándar de Python.

---

## Notas Importantes

- **No inventar person_key:** Solo usa person_key existentes
- **No recalcular elegibilidad/claims/pagos:** Solo conecta recovery con precondiciones (identidad+origen)
- **Todo auditable, idempotente, no destructivo**
- **Recovery solo puede:**
  - Crear vínculo canónico entre Lead Cabinet y person_key existente (via canon.identity_links)
  - Upsert canon.identity_origin (cabinet_lead + origin_source_id=lead_id)
  - Registrar en ops.cabinet_lead_recovery_audit
