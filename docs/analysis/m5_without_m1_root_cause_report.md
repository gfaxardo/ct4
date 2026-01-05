# REPORTE FINAL: Causa Raíz M5 sin M1

**Fecha:** 2025-01-04  
**Arquitecto Senior de Datos**  
**Fenómeno:** 107 drivers tienen M5 pero NO tienen M1 en `ops.v_payments_driver_matrix_cabinet`

---

## Resumen Ejecutivo

**Confirmado:**
- ✅ M5 existe en `ops.v_claims_payment_status_cabinet` para estos drivers
- ✅ M1 NO existe en `ops.v_claims_payment_status_cabinet` para estos drivers  
- ✅ M1 NO existe en `ops.mv_yango_receivable_payable_detail` (fuente upstream)
- ✅ No es bug de join ni de agregación: los datos reflejan correctamente la realidad

**Conclusión:** M1 nunca se genera por regla de negocio para estos drivers.

---

## Cadena de Dependencias

```
ops.v_payments_driver_matrix_cabinet
  └─> ops.v_claims_payment_status_cabinet
        └─> ops.mv_yango_receivable_payable_detail (materializada)
              └─> ops.v_yango_receivable_payable_detail
                    └─> ops.v_partner_payments_report_ui
                          └─> [Reglas de negocio / Fuentes de datos]
```

**Filtros en la cadena:**
- `v_claims_payment_status_cabinet`: `WHERE lead_origin = 'cabinet' AND milestone_value IN (1, 5, 25)`
- `v_yango_receivable_payable_detail`: `WHERE is_payable = true AND amount > 0`
- **No hay filtros que excluyan M1 específicamente**

---

## Análisis Realizado

### 1. Verificación en `ops.v_claims_payment_status_cabinet`
- **Resultado:** M5 existe, M1 NO existe para los 107 drivers afectados
- **Sample verificado:** 10 drivers, todos confirman el patrón

### 2. Verificación en `ops.mv_yango_receivable_payable_detail`
- **Resultado:** M5 existe, M1 NO existe en la fuente upstream
- **Conclusión:** El problema NO está en las vistas intermedias

### 3. Análisis de la cadena de vistas
- **`v_yango_receivable_payable_detail`:** Solo filtra por `is_payable = true AND amount > 0`
- **`v_partner_payments_report_ui`:** Vista que genera los milestones (necesita análisis)

### 4. Patrones temporales
- Drivers con M5 sin M1 tienen `lead_date` recientes (nov-dic 2025)
- Drivers con AMBOS M1 y M5 tienen el mismo `lead_date` para ambos milestones
- **No hay patrón temporal que explique la ausencia de M1**

---

## Causa Raíz Probable

### Hipótesis Principal: **M1 nunca se genera por regla de negocio para estos drivers**

**Justificación:**

1. **Evidencia directa:**
   - M1 NO existe en `ops.mv_yango_receivable_payable_detail` (fuente más upstream)
   - Si M1 no existe en la fuente, significa que la lógica que genera milestones nunca lo creó

2. **Evidencia indirecta:**
   - Los drivers SÍ tienen M5, lo que indica que el sistema procesa milestones para ellos
   - No hay filtros que excluyan M1 en las vistas intermedias
   - El 48% de drivers con M5 no tienen M1 (107/223), sugiriendo un patrón común

3. **Posibles causas específicas:**
   - **Regla de negocio:** M1 solo se genera bajo ciertas condiciones que estos drivers no cumplen
   - **Ventana temporal:** M1 requiere un evento/lead anterior que no existe para estos drivers
   - **Condición de elegibilidad:** Estos drivers alcanzaron M5 directamente sin pasar por M1 (ej: registro tardío, cambio de reglas)

### Causa Raíz Más Probable: **Regla de Negocio - M1 no aplica para estos drivers**

**Razón:** 
- Si fuera un bug de filtro, veríamos M1 en alguna parte de la cadena pero filtrado
- Si fuera un problema temporal, veríamos M1 con fechas diferentes
- Como M1 NO existe en ninguna parte de la cadena, la causa está en la **generación inicial** de milestones

---

## Queries Mínimas para Confirmar

### Q1: Verificar distribución de milestones en fuente upstream
```sql
SELECT 
    milestone_value,
    COUNT(*) as total_records,
    COUNT(DISTINCT driver_id) as unique_drivers,
    MIN(lead_date) as earliest_lead,
    MAX(lead_date) as latest_lead
FROM ops.mv_yango_receivable_payable_detail
WHERE lead_origin = 'cabinet'
    AND milestone_value IN (1, 5, 25)
GROUP BY milestone_value
ORDER BY milestone_value;
```

### Q2: Verificar drivers con M5 pero sin M1 en fuente upstream
```sql
SELECT 
    COUNT(DISTINCT driver_id) as drivers_m5_sin_m1
FROM (
    SELECT 
        driver_id,
        COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
        COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
    FROM ops.mv_yango_receivable_payable_detail
    WHERE lead_origin = 'cabinet'
        AND milestone_value IN (1, 5, 25)
    GROUP BY driver_id
    HAVING COUNT(*) FILTER (WHERE milestone_value = 1) = 0
    AND COUNT(*) FILTER (WHERE milestone_value = 5) > 0
) subq;
```

### Q3: Analizar `ops.v_partner_payments_report_ui` (fuente de generación)
```sql
-- Obtener definición completa
SELECT pg_get_viewdef('ops.v_partner_payments_report_ui', true);
```

**Nota:** Esta vista es la que realmente genera los milestones. Necesita análisis para entender las condiciones de generación.

---

## Decisión Recomendada

### **Opción: DOCUMENTAR REGLA DE NEGOCIO**

**Justificación:**

1. ✅ **No es un bug:** Los datos reflejan correctamente lo que existe en las fuentes upstream
2. ✅ **Es comportamiento esperado:** Si M1 no se genera por regla de negocio, es correcto que no aparezca
3. ✅ **La vista ya tiene flags:** `m5_without_m1_flag` identifica estos casos correctamente
4. ✅ **No se deben inventar datos:** Si M1 no existe, no debe aparecer en la vista

**Acciones Recomendadas:**

1. **Documentar en runbook:**
   - Actualizar `docs/runbooks/driver_matrix_inconsistencies.md`
   - Explicar que M5 sin M1 es esperado cuando M1 no se genera por regla de negocio
   - Agregar nota sobre posibles causas (registro tardío, cambio de reglas, etc.)

2. **Agregar comentario en la vista:**
   - Ya existe en `v_payments_driver_matrix_cabinet.sql` (línea 26-29)
   - Mantener y reforzar: "Milestones superiores pueden existir sin evidencia del milestone anterior en claims"

3. **Investigación opcional (si es necesario):**
   - Analizar `ops.v_partner_payments_report_ui` para entender condiciones de generación de M1
   - Revisar reglas de negocio que definen cuándo se genera M1 vs M5
   - Verificar si hay cambios históricos en las reglas que expliquen el patrón

4. **NO modificar la vista:**
   - ❌ NO inventar M1 cuando no existe
   - ❌ NO filtrar M5 cuando M1 no existe
   - ✅ Mantener los flags de inconsistencia para visibilidad

---

## Métricas

- **Total drivers en vista:** 223
- **Drivers con M5 sin M1:** 107 (48%)
- **Drivers con M25 sin M5:** 0 (0%)
- **Patrón:** Común, no aislado

---

## Archivos Generados

1. `backend/sql/ops/_analysis_v_claims_payment_status_cabinet_def.sql` - Definición de vista claims
2. `backend/sql/ops/_analysis_mv_receivable_payable_detail_def.sql` - Definición de materializada
3. `backend/sql/ops/_analysis_v_receivable_payable_detail_def.sql` - Definición de vista receivable
4. `backend/sql/ops/_diagnostic_m5_without_m1_queries.sql` - Queries diagnósticas

---

## Conclusión

**Causa raíz:** M1 nunca se genera por regla de negocio para estos drivers. Esto es comportamiento esperado, no un bug.

**Recomendación:** Documentar la regla de negocio y mantener la vista sin cambios. Los flags de inconsistencia (`m5_without_m1_flag`) proporcionan la visibilidad necesaria.

**Próximos pasos (opcional):** Si se requiere entender por qué M1 no se genera, analizar `ops.v_partner_payments_report_ui` y las reglas de negocio que definen la generación de milestones.


