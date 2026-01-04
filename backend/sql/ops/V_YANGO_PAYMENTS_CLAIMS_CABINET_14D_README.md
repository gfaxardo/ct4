# Vista: ops.v_yango_payments_claims_cabinet_14d

## Descripción

Vista de claims de pagos Yango Cabinet (ventana 14 días). Separa `paid_confirmed` (identity_status='confirmed' desde upstream) vs `paid_enriched` (identity_status='enriched' por matching por nombre).

## Cambios Aplicados

### Aliases de Compatibilidad

Se agregaron los siguientes aliases para compatibilidad con queries legacy:

- **`is_paid`**: Alias de `paid_is_paid` para queries que esperan `is_paid` directamente
- **`identity_status`**: Estado de identidad desde el ledger (confirmed/enriched/ambiguous/no_match)
- **`match_rule`**: Regla de matching usada (desde ledger)
- **`match_confidence`**: Nivel de confianza del matching (desde ledger)

### Columnas Principales

La vista expone las siguientes columnas:

**Identificadores:**
- `driver_id`, `person_key`
- `lead_date`, `pay_week_start_monday`, `milestone_value`

**Montos:**
- `expected_amount`, `currency`

**Estado de Pago:**
- `paid_status`: 'paid_confirmed' | 'paid_enriched' | 'pending_active' | 'pending_expired'
- `paid_is_paid`: boolean (alias: `is_paid`)
- `is_paid_effective`: boolean (solo confirmed cuenta como paid real)
- `is_paid_confirmed`: boolean
- `is_paid_enriched`: boolean

**Campos de Pago:**
- `paid_payment_key`, `paid_payment_key_confirmed`, `paid_payment_key_enriched`
- `paid_date`, `paid_date_confirmed`, `paid_date_enriched`

**Identidad:**
- `identity_status`: Estado de identidad
- `match_rule`: Regla de matching
- `match_confidence`: Nivel de confianza
- `match_method`: Método de matching ('driver_id', 'person_key', 'driver_id_enriched', 'person_key_enriched', 'none')

## Aplicación del SQL

### Paso 1: Ejecutar el SQL

```bash
# Desde psql o pgAdmin, ejecutar:
psql -U tu_usuario -d tu_database -f backend/sql/ops/v_yango_payments_claims_cabinet_14d.sql
```

O copiar y pegar el contenido del archivo `v_yango_payments_claims_cabinet_14d.sql` en tu cliente SQL.

### Paso 2: Verificar la Vista

Ejecutar las queries de verificación incluidas al final del archivo SQL:

```sql
-- Verificar que la vista existe y tiene datos
SELECT 
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_is_paid_true,
    COUNT(*) FILTER (WHERE paid_is_paid = true) AS count_paid_is_paid_true,
    COALESCE(SUM(expected_amount), 0) AS total_expected_amount,
    COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed') AS count_paid_confirmed,
    COUNT(*) FILTER (WHERE paid_status = 'paid_enriched') AS count_paid_enriched,
    COUNT(*) FILTER (WHERE paid_status = 'pending_active') AS count_pending_active,
    COUNT(*) FILTER (WHERE paid_status = 'pending_expired') AS count_pending_expired
FROM ops.v_yango_payments_claims_cabinet_14d;
```

### Paso 3: Validar Columnas Esperadas

Verificar que todas las columnas esperadas por el backend existan:

```sql
-- Verificar estructura de la vista
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'ops' 
  AND table_name = 'v_yango_payments_claims_cabinet_14d'
ORDER BY ordinal_position;
```

**Columnas requeridas por el backend:**
- ✅ `is_paid` (alias de `paid_is_paid`)
- ✅ `paid_is_paid`
- ✅ `is_paid_effective`
- ✅ `paid_payment_key`
- ✅ `paid_date`
- ✅ `paid_status`
- ✅ `identity_status`
- ✅ `match_rule`
- ✅ `match_confidence`

### Paso 4: Probar Queries del Backend

```sql
-- Query del endpoint summary (modo 'real')
SELECT 
    pay_week_start_monday,
    milestone_value,
    SUM(expected_amount) AS amount_expected_sum,
    SUM(CASE WHEN paid_status = 'paid_confirmed' THEN expected_amount ELSE 0 END) AS amount_paid_confirmed_sum,
    SUM(CASE WHEN paid_status = 'paid_enriched' THEN expected_amount ELSE 0 END) AS amount_paid_enriched_sum,
    COUNT(*) FILTER (WHERE paid_status IN ('paid_confirmed', 'paid_enriched')) AS count_paid
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY pay_week_start_monday, milestone_value
LIMIT 10;

-- Query del endpoint items (verificar que is_paid funciona)
SELECT 
    driver_id,
    paid_status,
    is_paid,
    paid_is_paid,
    is_paid_effective,
    identity_status,
    match_rule,
    match_confidence
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE is_paid = true  -- Debe funcionar ahora
LIMIT 10;
```

## Troubleshooting

### Error: "column is_paid does not exist"

**Causa**: La vista no tiene el alias `is_paid`.

**Solución**: Ejecutar el SQL actualizado que incluye el alias `is_paid = paid_is_paid`.

### Error: "column identity_status does not exist"

**Causa**: La vista no expone los campos de identidad del ledger.

**Solución**: El SQL actualizado ya incluye `identity_status`, `match_rule`, y `match_confidence`.

### La vista no se actualiza

**Causa**: Puede haber dependencias (otras vistas que dependen de esta).

**Solución**: El SQL usa `DROP VIEW IF EXISTS ... CASCADE` para eliminar dependencias, luego `CREATE OR REPLACE VIEW` para recrearla.

## Notas

- La vista es **idempotente**: puede ejecutarse múltiples veces sin errores.
- El filtro de fecha por defecto es agresivo (última semana) para performance en UI.
- Los campos `identity_status`, `match_rule`, `match_confidence` vienen del ledger enriquecido.
- El alias `is_paid` es para compatibilidad con queries legacy; preferir `paid_is_paid` o `is_paid_effective` en código nuevo.









