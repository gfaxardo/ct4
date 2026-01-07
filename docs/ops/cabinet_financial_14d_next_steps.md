# Siguientes Pasos - Cabinet Financial 14d

## ✅ Pasos Completados

### 1. Vista Canónica Creada
- ✅ `ops.v_cabinet_financial_14d` - Vista canónica financiera
- ✅ Verificada: 518 drivers de cabinet
- ✅ Funcional y lista para uso

### 2. Scripts de Verificación
- ✅ `backend/scripts/sql/verify_cabinet_financial_14d.sql` - Script completo
- ✅ `backend/scripts/verify_cabinet_financial_14d_simple.py` - Script simplificado
- ✅ Verificación ejecutada exitosamente

### 3. Optimización de Rendimiento
- ✅ Índices creados en `public.summary_daily`
- ✅ Vista materializada `ops.mv_cabinet_financial_14d` creada
- ✅ Índices en vista materializada creados

### 4. Documentación
- ✅ `docs/ops/cabinet_financial_14d_model.md` - Documentación completa del modelo

## 📋 Próximos Pasos Recomendados

### Paso 1: Refrescar Vista Materializada Periódicamente

La vista materializada debe refrescarse diariamente o después de actualizaciones de claims:

```bash
# Opción 1: Usar script Python
cd backend
python scripts/refresh_mv_cabinet_financial_14d.py

# Opción 2: SQL directo
psql -h 168.119.226.236 -U yego_user -d yego_integral -c "REFRESH MATERIALIZED VIEW ops.mv_cabinet_financial_14d;"
```

**Recomendación:** Configurar un job programado (cron/task scheduler) para refrescar diariamente.

### Paso 2: Integrar con Reportes Financieros

Usar la vista para generar reportes de cobranza a Yango:

```sql
-- Reporte de deuda pendiente
SELECT 
    driver_id,
    lead_date,
    total_trips_14d,
    expected_total_yango,
    total_paid_yango,
    amount_due_yango
FROM ops.mv_cabinet_financial_14d  -- Usar MV para mejor rendimiento
WHERE amount_due_yango > 0
ORDER BY amount_due_yango DESC;
```

### Paso 3: Monitoreo Continuo

Ejecutar el script de verificación periódicamente:

```bash
cd backend
python scripts/verify_cabinet_financial_14d_simple.py
```

**Frecuencia recomendada:**
- Semanalmente para monitoreo de cobranza
- Antes de reportes financieros a Yango
- Después de cambios en las vistas base

### Paso 4: Integración con Frontend (Opcional)

Si se requiere mostrar esta información en el dashboard:

1. Crear endpoint API en `backend/app/api/v1/`
2. Exponer datos de `ops.mv_cabinet_financial_14d`
3. Crear componente React en `frontend/components/`

### Paso 5: Automatización de Refresh

Configurar refresh automático de la vista materializada:

**Windows Task Scheduler:**
- Crear tarea que ejecute `refresh_mv_cabinet_financial_14d.py` diariamente

**Linux Cron:**
```cron
0 2 * * * cd /path/to/backend && python scripts/refresh_mv_cabinet_financial_14d.py
```

## 📊 Métricas Actuales

Según la última verificación:

- **Total drivers cabinet:** 518
- **Drivers con deuda esperada:** 116
- **Drivers con deuda pendiente:** 70
- **Total esperado Yango:** S/ 9,865.00
- **Total pagado Yango:** S/ 4,140.00
- **Total deuda Yango:** S/ 5,725.00
- **Porcentaje de cobranza:** 41.97%

## 🔍 Consultas Útiles

### Top 10 Drivers con Mayor Deuda

```sql
SELECT 
    driver_id,
    lead_date,
    total_trips_14d,
    expected_total_yango,
    total_paid_yango,
    amount_due_yango
FROM ops.mv_cabinet_financial_14d
WHERE amount_due_yango > 0
ORDER BY amount_due_yango DESC
LIMIT 10;
```

### Resumen por Milestone

```sql
SELECT 
    'M1' AS milestone,
    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_reached,
    COUNT(CASE WHEN claim_m1_paid = true THEN 1 END) AS drivers_paid,
    SUM(expected_amount_m1) AS total_expected,
    SUM(paid_amount_m1) AS total_paid,
    SUM(expected_amount_m1 - paid_amount_m1) AS total_due
FROM ops.mv_cabinet_financial_14d
WHERE reached_m1_14d = true;
```

### Drivers con Milestones Alcanzados sin Claim

```sql
SELECT 
    driver_id,
    lead_date,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    expected_total_yango
FROM ops.mv_cabinet_financial_14d
WHERE (reached_m1_14d = true AND claim_m1_exists = false)
    OR (reached_m5_14d = true AND claim_m5_exists = false)
    OR (reached_m25_14d = true AND claim_m25_exists = false);
```

## 📝 Notas Importantes

1. **Vista vs Vista Materializada:**
   - Usar `ops.v_cabinet_financial_14d` para datos en tiempo real
   - Usar `ops.mv_cabinet_financial_14d` para reportes y dashboards (mejor rendimiento)

2. **Refresh de Vista Materializada:**
   - El refresh bloquea la vista durante la actualización
   - Para grandes volúmenes, considerar refresh CONCURRENTLY (requiere índices únicos)

3. **Monitoreo:**
   - Verificar periódicamente inconsistencias entre viajes y claims
   - Monitorear el porcentaje de cobranza

4. **Mantenimiento:**
   - Los índices se mantienen automáticamente por PostgreSQL
   - La vista materializada requiere refresh manual o programado

## 🎯 Objetivo Cumplido

La fuente de verdad financiera está operativa y permite responder sin ambigüedad:

> **"Yango nos debe S/ 5,725.00 por 70 drivers y sus hitos correspondientes"**

La vista está lista para uso en producción para reportes financieros y cobranza a Yango.



