# Fix: M1 Achieved Flag - Resumen de Cambios

## Problema Identificado

Los flags `achieved` (M1/M5/M25) en `ops.v_payments_driver_matrix_cabinet` provenían de `ops.v_claims_payment_status_cabinet`, que a su vez filtraba por `milestone_achieved = true` desde `ops.v_payment_calculation`. 

El problema: `v_payment_calculation` define `milestone_achieved` basándose en:
- Viajes dentro de una ventana de pago específica
- Existencia de un evento lead correspondiente

Esto causaba que M1 no se marcara como "achieved" en la UI cuando:
- El milestone fue alcanzado por viajes reales
- Pero no cumplía con las reglas de pago (sin lead, fuera de ventana, etc.)

## Solución Implementada

**Separación de responsabilidades:**
- **Flags achieved**: Ahora provienen de `ops.v_cabinet_milestones_achieved_from_trips` (determinísticos basados en viajes reales)
- **Payment info**: Sigue viniendo de `ops.v_claims_payment_status_cabinet` (reglas de negocio y ventanas)

### Cambios en `ops.v_payments_driver_matrix_cabinet`

1. **Nuevo CTE `deterministic_milestones`**: Obtiene milestones desde `v_cabinet_milestones_achieved_from_trips`
2. **Nuevo CTE `deterministic_milestones_agg`**: Agrega milestones determinísticos por `driver_id`
3. **Nuevo CTE `claims_agg`**: Agrega claims por `driver_id` (solo para payment info)
4. **CTE `driver_milestones` modificado**:
   - Usa `FULL OUTER JOIN` entre `deterministic_milestones_agg` y `claims_agg`
   - Flags achieved (`m1_achieved_flag`, `m5_achieved_flag`, `m25_achieved_flag`) y `achieved_date` vienen de `deterministic_milestones_agg`
   - Payment info (`expected_amount`, `payment_status`, `window_status`, `overdue_days`) viene de `claims_agg`

### Archivos Modificados

1. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Modificado: Lógica de agregación y fuente de flags achieved
   - Actualizado: Comentarios de columnas para reflejar nueva fuente

2. **`backend/scripts/sql/verify_m1_achieved_fix.sql`** (nuevo)
   - Script de verificación con 5 queries:
     - Query 1: Detectar inconsistencias M1 (debe retornar 0 filas)
     - Query 2: Ejemplos de drivers con M1 achieved
     - Query 3: Comparación M1 vs M5
     - Query 4: Conteo de drivers por estado M1
     - Query 5: Drivers con M5 achieved pero sin M1

## Comandos para Aplicar el Fix

### 1. Aplicar la Vista Modificada

```bash
# Desde el directorio del proyecto
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

O usando el cliente SQL directamente:

```sql
-- Conectar a la base de datos
\c <database_name>

-- Ejecutar el script
\i backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 2. Verificar el Fix

```bash
# Ejecutar script de verificación
psql $DATABASE_URL -f backend/scripts/sql/verify_m1_achieved_fix.sql
```

**Resultado esperado:**
- Query 1 debe retornar **0 filas** (no hay inconsistencias M1)
- Query 5 debe retornar **0 o muy bajo** (M5 sin M1 no debería ocurrir con la vista determinística)

### 3. Verificar en la UI

1. Abrir `/pagos/driver-matrix` o `/pagos/resumen-conductor`
2. Verificar que drivers con M1 achieved (según viajes reales) ahora muestran el flag "Alcanzado"
3. Verificar que la información de pagos (montos, estados, ventanas) sigue funcionando correctamente

## Diferencias Clave

### Antes
```sql
-- Flags achieved desde base_claims (que filtra por milestone_achieved = true)
BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag,
MAX(CASE WHEN bc.milestone_value = 1 THEN bc.lead_date END) AS m1_achieved_date,
```

### Después
```sql
-- Flags achieved desde deterministic_milestones_agg (determinísticos)
COALESCE(dma.m1_achieved_flag, false) AS m1_achieved_flag,
dma.m1_achieved_date,
```

## Notas Importantes

1. **No se modificaron**:
   - `ops.v_payment_calculation` (sigue siendo canónica para pagos)
   - `ops.v_claims_payment_status_cabinet` (sigue siendo canónica para claims)
   - Lógica de reglas ni ventanas

2. **Flags de inconsistencia**:
   - `m5_without_m1_flag` y `m25_without_m5_flag` ahora se basan en flags determinísticos
   - Con la vista determinística, estas inconsistencias **NO deberían ocurrir** porque `v_cabinet_milestones_achieved_from_trips` expande milestones menores
   - Se mantienen por compatibilidad y para detectar posibles bugs

3. **Performance**:
   - La vista ahora hace un `FULL OUTER JOIN` entre milestones determinísticos y claims
   - Esto puede afectar performance si hay muchos drivers sin claims
   - Si es necesario, considerar crear índices o materializar la vista

## Rollback (si es necesario)

Si necesitas revertir el cambio:

```sql
-- Restaurar desde git
git checkout HEAD -- backend/sql/ops/v_payments_driver_matrix_cabinet.sql

-- Re-ejecutar la vista original
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

## Próximos Pasos

1. ✅ Aplicar la vista modificada
2. ✅ Ejecutar script de verificación
3. ✅ Validar en UI que M1 ahora se marca correctamente
4. ⏳ Monitorear performance de la vista
5. ⏳ Considerar crear índices si es necesario


