# Capa Operativa 14d Sanity Check y Driver Matrix

## Problema que Resuelve

Esta capa operativa resuelve la necesidad de validar visualmente y técnicamente que:
1. La conexión ocurrió dentro de la ventana de 14 días
2. Los viajes reales dentro de 14 días cuadran con M1 / M5 / M25
3. No existan claims "fantasma" ni achieved inconsistentes
4. La UI muestre información coherente y explicable

## Conceptos Clave: Achieved ≠ Claim ≠ Paid

### Achieved
- **Definición**: Cumplimiento de meta basado en viajes reales
- **Source-of-truth**: `ops.v_cabinet_milestones_achieved_from_payment_calc`
- **Cálculo**: Basado en `ops.v_payment_calculation` que usa `summary_daily` (viajes reales)
- **Ventana**: 14 días desde `lead_date`
- **Ejemplo**: Driver logra 5 viajes dentro de 14 días → `m5_achieved_flag = true`

### Claim
- **Definición**: Registro cobrable/reclamo con expected_amount, due_date, status
- **Source-of-truth**: `ops.v_claims_payment_status_cabinet`
- **Cálculo**: Basado en achieved dentro de ventana de 14 días
- **Ventana**: 14 días desde `lead_date`
- **Status**: UNPAID, PAID, PAID_MISAPPLIED
- **Ejemplo**: Driver con M5 achieved → genera claim M5 con `expected_amount = 35`, `status = UNPAID`

### Paid
- **Definición**: Pago conciliado desde ledger
- **Source-of-truth**: `ops.v_yango_payments_ledger_latest_enriched`
- **Cálculo**: Matching entre claim y pago por driver_id + milestone_value
- **Ejemplo**: Claim M5 UNPAID → si hay pago conciliado → `status = PAID`

## Por Qué summary_daily es la Fuente Operativa

`public.summary_daily` es la fuente operativa porque:
1. **Viajes reales**: `count_orders_completed` refleja viajes realmente completados
2. **Fecha normalizada**: `date_file` (formato DD-MM-YYYY) se normaliza con `to_date()`
3. **Conexión real**: `sum_work_time_seconds > 0` o `count_orders_completed > 0` indica conexión real
4. **Ventana precisa**: Permite calcular viajes exactos dentro de 14 días desde `lead_date`

## Nueva Vista: ops.v_cabinet_ops_14d_sanity

### Propósito
Capa operativa de SANITY CHECK alineada a CLAIMS (ventana de 14 días). Proporciona métricas operativas basadas en viajes reales para validar coherencia.

### Grano
**1 fila por driver_id** (GARANTIZADO)

### Columnas

#### `connection_within_14d_flag`
- **Tipo**: `boolean`
- **Significado**: `true` si la conexión ocurrió dentro de la ventana de 14 días
- **Cálculo**: `first_connection_date_within_14d IS NOT NULL`
- **Uso**: Validar que conexión ocurrió dentro de ventana

#### `connection_date_within_14d`
- **Tipo**: `date`
- **Significado**: Primera fecha de conexión dentro de la ventana de 14 días
- **Cálculo**: `MIN(prod_date)` donde `has_connection = 1` y `prod_date` dentro de ventana
- **Uso**: Fecha exacta de conexión dentro de ventana (NULL si fuera de ventana)

#### `trips_completed_14d_from_lead`
- **Tipo**: `integer`
- **Significado**: Total de viajes completados dentro de la ventana de 14 días
- **Cálculo**: `SUM(count_orders_completed)` donde `prod_date` dentro de ventana
- **Uso**: Validar que achieved flags se sustentan en viajes reales

#### `first_trip_date_within_14d`
- **Tipo**: `date`
- **Significado**: Primera fecha con viaje completado dentro de la ventana
- **Cálculo**: `MIN(prod_date)` donde `count_orders_completed > 0` y `prod_date` dentro de ventana
- **Uso**: Fecha exacta del primer viaje dentro de ventana (NULL si no hubo viajes)

## Cómo Leer las Nuevas Columnas en Driver Matrix

### Ejemplo 1: M1 Achieved Correcto

```
driver_id: abc123
lead_date: 2025-12-01
connection_within_14d_flag: true
connection_date_within_14d: 2025-12-02
trips_completed_14d_from_lead: 3
first_trip_date_within_14d: 2025-12-02
m1_achieved_flag: true
m1_yango_payment_status: UNPAID
```

**Interpretación**:
- ✅ Conexión dentro de ventana (2025-12-02, dentro de 14 días desde 2025-12-01)
- ✅ 3 viajes dentro de ventana → M1 achieved correcto (≥ 1 viaje)
- ✅ Claim M1 generado (UNPAID) → correcto
- ✅ Coherencia: achieved, trips y claim alineados

### Ejemplo 2: M5 Claim Correcto

```
driver_id: def456
lead_date: 2025-12-01
trips_completed_14d_from_lead: 7
m5_achieved_flag: true
m5_yango_payment_status: UNPAID
m5_expected_amount_yango: 35.00
```

**Interpretación**:
- ✅ 7 viajes dentro de ventana → M5 achieved correcto (≥ 5 viajes)
- ✅ Claim M5 generado (UNPAID, S/ 35.00) → correcto
- ✅ Coherencia: trips (7) ≥ milestone (5), claim existe

### Ejemplo 3: M5 Claim Incorrecto (Fantasma)

```
driver_id: ghi789
lead_date: 2025-12-01
trips_completed_14d_from_lead: 3
m5_achieved_flag: false
m5_yango_payment_status: UNPAID  -- ⚠️ INCONSISTENCIA
m5_expected_amount_yango: 35.00
```

**Interpretación**:
- ⚠️ Solo 3 viajes dentro de ventana → M5 NO debería estar achieved
- ⚠️ Pero existe claim M5 → INCONSISTENCIA (claim fantasma)
- ❌ Debe investigarse: ¿por qué se generó claim sin achieved?

### Ejemplo 4: M1 Achieved sin Claim (Fuera de Ventana)

```
driver_id: jkl012
lead_date: 2025-11-01
connection_within_14d_flag: false
connection_date_within_14d: NULL
trips_completed_14d_from_lead: 0
first_trip_date_within_14d: NULL
m1_achieved_flag: false
m1_yango_payment_status: NULL
```

**Interpretación**:
- ✅ No hubo conexión dentro de ventana (14 días desde 2025-11-01)
- ✅ 0 viajes dentro de ventana → M1 NO achieved
- ✅ No hay claim M1 → correcto (no se genera claim si no está achieved dentro de ventana)

## Validaciones Implementadas

### Script 1: verify_ops_14d_sanity.sql
- **CHECK A**: M1 achieved pero trips < 1 → esperado 0
- **CHECK B**: M5 achieved pero trips < 5 → esperado 0
- **CHECK C**: M25 achieved pero trips < 25 → esperado 0
- **CHECK D**: Connection flag true pero fecha fuera de ventana → esperado 0

### Script 2: verify_claims_vs_ops_consistency.sql
- **CHECK A**: Claim M1 pero trips = 0 → esperado 0
- **CHECK B**: Claim M5 pero trips < 5 → esperado 0
- **CHECK C**: Claim M25 pero trips < 25 → esperado 0

### Script 3: spot_check_driver_matrix_ops.sql
- Muestra 20 drivers con información operativa y de claims
- Usado para auditoría humana

## Uso en UI

Las nuevas columnas están disponibles en `ops.v_payments_driver_matrix_cabinet` y pueden ser:
1. **Mostradas directamente** en la tabla (si se agregan columnas)
2. **Usadas en tooltips** para explicar por qué un claim existe o no
3. **Filtradas** para encontrar inconsistencias
4. **Exportadas** en CSV para análisis

**Nota**: No se requiere modificar frontend para que estas columnas existan. Están disponibles en el endpoint `/api/v1/ops/payments/driver-matrix` y pueden ser usadas cuando sea necesario.

## Comandos de Verificación

```powershell
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"

# Verificar sanity check
& $psql $DATABASE_URL -f backend/scripts/sql/verify_ops_14d_sanity.sql

# Verificar consistencia claims vs ops
& $psql $DATABASE_URL -f backend/scripts/sql/verify_claims_vs_ops_consistency.sql

# Spot-check
& $psql $DATABASE_URL -f backend/scripts/sql/spot_check_driver_matrix_ops.sql
```

## Resultados Esperados

### verify_ops_14d_sanity.sql
- CHECK A: `count_inconsistencies = 0` ✓ PASS
- CHECK B: `count_inconsistencies = 0` ✓ PASS
- CHECK C: `count_inconsistencies = 0` ✓ PASS
- CHECK D: `count_inconsistencies = 0` ✓ PASS

### verify_claims_vs_ops_consistency.sql
- CHECK A: `count_inconsistencies = 0` ✓ PASS
- CHECK B: `count_inconsistencies = 0` ✓ PASS
- CHECK C: `count_inconsistencies = 0` ✓ PASS

### spot_check_driver_matrix_ops.sql
- Muestra 20 drivers con información completa para auditoría humana

