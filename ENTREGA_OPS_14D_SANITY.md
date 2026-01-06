# Entrega Final: Capa Operativa 14d Sanity Check

## Archivos Creados/Modificados

### Vistas SQL Creadas
1. **`backend/sql/ops/v_cabinet_ops_14d_sanity.sql`**
   - Nueva vista operativa de sanity check
   - Grano: 1 fila por driver_id
   - Columnas: `connection_within_14d_flag`, `connection_date_within_14d`, `trips_completed_14d_from_lead`, `first_trip_date_within_14d`

### Vistas SQL Modificadas
2. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Enriquecida con LEFT JOIN a `ops.v_cabinet_ops_14d_sanity`
   - Nuevas columnas expuestas: `connection_within_14d_flag`, `connection_date_within_14d`, `trips_completed_14d_from_lead`, `first_trip_date_within_14d`
   - Mantiene grano: 1 fila por driver_id
   - No modifica lógica de achieved ni payment

### Scripts de Verificación Creados
3. **`backend/scripts/sql/verify_ops_14d_sanity.sql`**
   - CHECK A: M1 achieved pero trips < 1 → esperado 0
   - CHECK B: M5 achieved pero trips < 5 → esperado 0
   - CHECK C: M25 achieved pero trips < 25 → esperado 0
   - CHECK D: Connection flag true pero fecha fuera de ventana → esperado 0
   - RESUMEN: Distribución de achieved vs trips

4. **`backend/scripts/sql/verify_claims_vs_ops_consistency.sql`**
   - CHECK A: Claim M1 pero trips = 0 → esperado 0
   - CHECK B: Claim M5 pero trips < 5 → esperado 0
   - CHECK C: Claim M25 pero trips < 25 → esperado 0
   - RESUMEN: Distribución de claims vs trips

5. **`backend/scripts/sql/spot_check_driver_matrix_ops.sql`**
   - Spot-check de 20 drivers con información operativa y de claims
   - Usado para auditoría humana

### Documentación Creada
6. **`OPS_14D_SANITY_AND_DRIVER_MATRIX.md`**
   - Documentación completa de la capa operativa
   - Explicación de conceptos: Achieved ≠ Claim ≠ Paid
   - Ejemplos de interpretación
   - Guía de uso

## Comandos para Aplicar

### 1. Aplicar Vista Nueva
```powershell
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"

# Crear vista de sanity check
& $psql $DATABASE_URL -f backend/sql/ops/v_cabinet_ops_14d_sanity.sql
```

### 2. Aplicar Modificación a Driver Matrix
```powershell
# Modificar driver_matrix para incluir columnas operativas
& $psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 3. Ejecutar Verificaciones
```powershell
# Verificar sanity check (achieved vs trips)
& $psql $DATABASE_URL -f backend/scripts/sql/verify_ops_14d_sanity.sql

# Verificar consistencia claims vs ops
& $psql $DATABASE_URL -f backend/scripts/sql/verify_claims_vs_ops_consistency.sql

# Spot-check para auditoría
& $psql $DATABASE_URL -f backend/scripts/sql/spot_check_driver_matrix_ops.sql
```

## Resultados Esperados

### verify_ops_14d_sanity.sql

#### CHECK A: M1 achieved pero trips < 1
```
check_name                              | count_inconsistencies | status
----------------------------------------+-----------------------+--------
CHECK A: M1 achieved pero trips < 1     | 0                     | ✓ PASS
```

#### CHECK B: M5 achieved pero trips < 5
```
check_name                              | count_inconsistencies | status
----------------------------------------+-----------------------+--------
CHECK B: M5 achieved pero trips < 5    | 0                     | ✓ PASS
```

#### CHECK C: M25 achieved pero trips < 25
```
check_name                              | count_inconsistencies | status
----------------------------------------+-----------------------+--------
CHECK C: M25 achieved pero trips < 25  | 0                     | ✓ PASS
```

#### CHECK D: Connection flag true pero fecha fuera de ventana
```
check_name                                              | count_inconsistencies | status
--------------------------------------------------------+-----------------------+--------
CHECK D: Connection flag true pero fecha fuera de ventana | 0                  | ✓ PASS
```

#### RESUMEN: Distribución de achieved vs trips
```
check_name                    | m1_achieved_count | m1_achieved_with_trips_ok | m5_achieved_count | m5_achieved_with_trips_ok | m25_achieved_count | m25_achieved_with_trips_ok
------------------------------+--------------------+----------------------------+--------------------+----------------------------+---------------------+-----------------------------
RESUMEN: Achieved vs trips... | [N]                 | [N]                        | [N]                | [N]                        | [N]                 | [N]
```
**Nota**: `m1_achieved_count` debe ser igual a `m1_achieved_with_trips_ok` (y lo mismo para M5 y M25).

### verify_claims_vs_ops_consistency.sql

#### CHECK A: Claim M1 pero trips = 0
```
check_name                    | count_inconsistencies | status
-------------------------------+-----------------------+--------
CHECK A: Claim M1 pero trips = 0 | 0                  | ✓ PASS
```

#### CHECK B: Claim M5 pero trips < 5
```
check_name                    | count_inconsistencies | status
-------------------------------+-----------------------+--------
CHECK B: Claim M5 pero trips < 5 | 0                  | ✓ PASS
```

#### CHECK C: Claim M25 pero trips < 25
```
check_name                     | count_inconsistencies | status
--------------------------------+-----------------------+--------
CHECK C: Claim M25 pero trips < 25 | 0                 | ✓ PASS
```

#### RESUMEN: Distribución de claims vs trips
```
check_name                    | m1_claims_count | m1_claims_with_trips_ok | m5_claims_count | m5_claims_with_trips_ok | m25_claims_count | m25_claims_with_trips_ok
------------------------------+-----------------+-------------------------+-----------------+-------------------------+------------------+--------------------------
RESUMEN: Claims vs trips...   | [N]             | [N]                     | [N]             | [N]                     | [N]              | [N]
```
**Nota**: `m1_claims_count` debe ser igual a `m1_claims_with_trips_ok` (y lo mismo para M5 y M25).

### spot_check_driver_matrix_ops.sql

Muestra 20 filas con:
- `driver_id`, `driver_name`, `lead_date`
- `connection_within_14d_flag`, `connection_date_within_14d`
- `trips_completed_14d_from_lead`, `first_trip_date_within_14d`
- `m1_achieved_flag`, `m5_achieved_flag`, `m25_achieved_flag`
- `m1_yango_payment_status`, `m5_yango_payment_status`, `m25_yango_payment_status`
- `m1_expected_amount_yango`, `m5_expected_amount_yango`, `m25_expected_amount_yango`

**Uso**: Auditoría humana para validar coherencia visual.

## Checklist Final para Validar en UI

### Visual (sin cambios en código)
1. ✅ **Driver Matrix carga correctamente**
   - Endpoint `/api/v1/ops/payments/driver-matrix` responde 200
   - Tabla muestra 1 fila por driver (sin duplicados)

2. ✅ **Columnas operativas disponibles** (si se agregan a la UI)
   - `connection_within_14d_flag` visible
   - `trips_completed_14d_from_lead` visible
   - `first_trip_date_within_14d` visible

3. ✅ **Coherencia visual**
   - Drivers con `m1_achieved_flag = true` tienen `trips_completed_14d_from_lead >= 1`
   - Drivers con `m5_achieved_flag = true` tienen `trips_completed_14d_from_lead >= 5`
   - Drivers con `m25_achieved_flag = true` tienen `trips_completed_14d_from_lead >= 25`

4. ✅ **Claims coherentes**
   - Drivers con `m1_yango_payment_status IS NOT NULL` tienen `trips_completed_14d_from_lead >= 1`
   - Drivers con `m5_yango_payment_status IS NOT NULL` tienen `trips_completed_14d_from_lead >= 5`
   - Drivers con `m25_yango_payment_status IS NOT NULL` tienen `trips_completed_14d_from_lead >= 25`

### Técnico (scripts SQL)
5. ✅ **Todos los checks pasan**
   - `verify_ops_14d_sanity.sql` → todos PASS
   - `verify_claims_vs_ops_consistency.sql` → todos PASS

6. ✅ **No hay duplicados**
   - `SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet GROUP BY driver_id HAVING COUNT(*) > 1;` → 0 filas

7. ✅ **Vista de sanity check funciona**
   - `SELECT COUNT(*) FROM ops.v_cabinet_ops_14d_sanity;` → retorna número razonable
   - `SELECT COUNT(DISTINCT driver_id) FROM ops.v_cabinet_ops_14d_sanity;` → igual al COUNT(*)

## Notas Importantes

1. **No se modificó frontend**: Las nuevas columnas están disponibles en el endpoint pero no se requiere modificar UI para que funcionen.

2. **Grano preservado**: `v_payments_driver_matrix_cabinet` mantiene 1 fila por driver_id.

3. **No se rompió lógica existente**: Achieved flags y payment status no se modificaron.

4. **Ventana de 14 días**: Todas las métricas operativas usan la misma ventana que claims (14 días desde `lead_date`).

5. **Source-of-truth operativo**: `summary_daily` es la fuente de viajes reales, no `v_payment_calculation` (que puede tener reglas adicionales).

