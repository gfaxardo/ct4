# Diagnóstico: Yango Payment Ledger Desactualizado

## Problema Reportado

- **Yango Payment Ledger** se actualiza hasta el **18/12** (visible en health del sistema)
- **module_ct_cabinet_payments** es la fuente real de los pagos, pero **NO aparece en health**
- Hay un quiebre en la actualización entre ambas fuentes

## Análisis del Problema

### 1. Flujo de Datos Esperado

```
public.module_ct_cabinet_payments (fuente RAW)
    ↓
ops.v_yango_payments_raw_current (vista que normaliza)
    ↓
ops.v_yango_payments_raw_current_aliases (alias de la vista)
    ↓
ops.ingest_yango_payments_snapshot() (función de ingesta)
    ↓
ops.yango_payment_ledger (ledger histórico)
    ↓
ops.v_yango_payments_ledger_latest (vista del estado actual)
    ↓
ops.v_yango_payments_ledger_latest_enriched (vista enriquecida con identidad)
```

### 2. Problemas Identificados

#### A. `module_ct_cabinet_payments` NO está en Health Check

**Ubicación:** `backend/sql/ops/v_data_health.sql`

**Líneas 85-88 y 317-340:** `module_ct_cabinet_payments` está **COMENTADO** con la nota:
```sql
-- COMENTADO: public.module_ct_cabinet_payments existe pero tiene estructura diferente (no tiene pay_date)
```

**Razón del comentario:** La vista `v_data_health.sql` espera una columna `pay_date`, pero `module_ct_cabinet_payments` tiene una columna `date` (no `pay_date`).

**Evidencia:** En `backend/sql/ops/v_yango_payments_raw_current.sql` (línea 46), se mapea:
```sql
date AS pay_date,
```

**Solución:** Descomentar y corregir la CTE `source_module_ct_cabinet_payments` para usar `date` en lugar de `pay_date`.

#### B. No hay Proceso Automatizado de Ingesta

**Función de ingesta:** `ops.ingest_yango_payments_snapshot()` existe en `backend/sql/ops/ingest_yango_payments_snapshot.sql`

**Problema:** No hay evidencia de:
- Un job programado (cron/task scheduler) que ejecute esta función
- Un endpoint API que permita ejecutarla manualmente
- Un proceso automatizado que la ejecute periódicamente

**Resultado:** El ledger (`ops.yango_payment_ledger`) solo se actualiza cuando se ejecuta manualmente la función, por eso se quedó en el 18/12.

### 3. Verificaciones Necesarias

#### Verificar estructura real de `module_ct_cabinet_payments`:
```sql
SELECT column_name, data_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name = 'module_ct_cabinet_payments' 
ORDER BY ordinal_position;
```

#### Verificar fechas máximas:
```sql
-- En la fuente RAW
SELECT MAX(date) as max_date, MAX(created_at) as max_created_at
FROM public.module_ct_cabinet_payments;

-- En el ledger
SELECT MAX(pay_date) as max_pay_date, MAX(snapshot_at) as max_snapshot_at
FROM ops.yango_payment_ledger;
```

#### Verificar última ejecución de ingesta:
```sql
SELECT MAX(snapshot_at) as last_snapshot_at
FROM ops.yango_payment_ledger;
```

## Soluciones Propuestas

### Solución 1: Agregar `module_ct_cabinet_payments` al Health Check

**Archivo:** `backend/sql/ops/v_data_health.sql`

**Cambios necesarios:**
1. Descomentar la CTE `source_module_ct_cabinet_payments` (líneas 317-340)
2. Corregir la expresión de `business_date` para usar `date` en lugar de `pay_date`:
   ```sql
   MAX(date) AS max_business_date,  -- En lugar de pay_date
   ```
3. Descomentar la línea en UNION ALL (línea 403)

### Solución 2: Crear Endpoint API para Ejecutar Ingesta

**Archivo:** `backend/app/api/v1/ops.py`

**Agregar endpoint:**
```python
@router.post("/yango-payments/ingest")
def ingest_yango_payments(db: Session = Depends(get_db)):
    """
    Ejecuta la ingesta de pagos Yango desde module_ct_cabinet_payments al ledger.
    """
    try:
        result = db.execute(text("SELECT ops.ingest_yango_payments_snapshot()"))
        rows_inserted = result.scalar()
        return {"status": "success", "rows_inserted": rows_inserted}
    except Exception as e:
        logger.exception("ingest_yango_payments failed")
        raise HTTPException(status_code=500, detail=str(e))
```

### Solución 3: Crear Proceso Automatizado

**Opción A: Task Scheduler (Windows)**
- Crear script PowerShell que ejecute la función vía API o directamente en PostgreSQL
- Programar ejecución cada hora o cada 6 horas

**Opción B: Cron Job (Linux)**
- Crear script bash que ejecute la función
- Programar en crontab

**Opción C: Job dentro de la aplicación**
- Usar APScheduler o similar para ejecutar la función periódicamente
- Integrar con el sistema de jobs existente (`ops.ingestion_runs`)

### Solución 4: Verificar y Corregir Estructura de Datos

Si `module_ct_cabinet_payments` realmente no tiene `date` o tiene otra estructura:
1. Verificar estructura real de la tabla
2. Ajustar `v_yango_payments_raw_current.sql` si es necesario
3. Ajustar `v_data_health.sql` para reflejar la estructura real

## Plan de Acción

1. ✅ **Verificar estructura real** de `module_ct_cabinet_payments`
2. ✅ **Verificar fechas máximas** en ambas fuentes
3. ✅ **Descomentar y corregir** `module_ct_cabinet_payments` en `v_data_health.sql`
4. ✅ **Crear endpoint API** para ejecutar ingesta manualmente
5. ✅ **Crear script Python** para automatizar la ingesta periódicamente
6. ⏳ **Ejecutar ingesta manualmente** para actualizar el ledger hasta la fecha actual
7. ⏳ **Configurar proceso automatizado** (cron/task scheduler) para ejecutar ingesta periódicamente
8. ⏳ **Verificar que el health check** muestre ambas fuentes correctamente

## Cambios Implementados

### 1. Corrección de `v_data_health.sql`

**Archivo:** `backend/sql/ops/v_data_health.sql`

**Cambios:**
- ✅ Descomentada la entrada de `module_ct_cabinet_payments` en `v_data_sources_catalog` (línea 85-88)
- ✅ Descomentada y corregida la CTE `source_module_ct_cabinet_payments` (líneas 317-340)
- ✅ Corregida para usar `date` en lugar de `pay_date` (la tabla tiene columna `date`, no `pay_date`)
- ✅ Descomentada la línea en UNION ALL para incluir `module_ct_cabinet_payments` en los resultados
- ✅ Descomentada y corregida la CTE `source_module_ct_cabinet_payments_daily` (líneas 594-614)
- ✅ Agregados `DROP VIEW IF EXISTS ... CASCADE` antes de cada `CREATE VIEW` para permitir recreación

**Resultado:** `module_ct_cabinet_payments` ahora aparece en el health check del sistema.

### 2. Endpoint API para Ingesta Manual

**Archivo:** `backend/app/api/v1/ops.py`

**Nuevo endpoint:**
```python
POST /api/v1/ops/yango-payments/ingest
```

**Funcionalidad:**
- Ejecuta `ops.ingest_yango_payments_snapshot()`
- Retorna número de filas insertadas
- Permite ejecución manual desde el frontend o curl

### 3. Script Python para Automatización

**Archivo:** `backend/scripts/ingest_yango_payments.py`

**Funcionalidad:**
- Ejecuta la función `ops.ingest_yango_payments_snapshot()`
- Puede ser ejecutado manualmente o programado en cron/task scheduler
- Incluye logging de resultados

**Uso:**
```bash
python backend/scripts/ingest_yango_payments.py
```

**Para automatizar (Windows Task Scheduler):**
- Programar ejecución cada hora o cada 6 horas
- Usar el script Python directamente o crear un wrapper .bat/.ps1

**Para automatizar (Linux cron):**
```bash
# Ejecutar cada hora
0 * * * * cd /path/to/CT4/backend && python scripts/ingest_yango_payments.py
```

## Próximos Pasos

1. **Ejecutar ingesta manualmente** para actualizar el ledger:
   ```bash
   python backend/scripts/ingest_yango_payments.py
   ```
   O vía API:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ops/yango-payments/ingest"
   ```

2. **Verificar que el health check muestre ambas fuentes:**
   - Navegar a `/ops/health?tab=raw` en el frontend
   - Verificar que `module_ct_cabinet_payments` aparece en la lista
   - Verificar que `yango_payment_ledger` también aparece

3. **Configurar proceso automatizado:**
   - Elegir método (Windows Task Scheduler o Linux cron)
   - Programar ejecución periódica (recomendado: cada hora)
   - Monitorear logs para verificar que se ejecuta correctamente

4. **Monitorear el gap entre fuentes:**
   - Si `module_ct_cabinet_payments` tiene datos más recientes que `yango_payment_ledger`, significa que la ingesta no se está ejecutando automáticamente
   - Si ambas fuentes están sincronizadas, el proceso automatizado está funcionando correctamente

## Notas Adicionales

- El health check actual muestra `yango_payment_ledger` (el ledger procesado), pero no muestra `module_ct_cabinet_payments` (la fuente RAW)
- Esto es problemático porque no se puede detectar si la fuente RAW tiene datos nuevos que no se han procesado
- La solución requiere tanto corregir el health check como automatizar la ingesta

