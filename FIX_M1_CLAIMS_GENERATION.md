# Fix: Generación de Claims M1 para Cabinet

## Problema Identificado

Para `origin_tag='cabinet'`, el sistema generaba claims para M5 y M25 pero **NO generaba claims para M1**, aunque M1 estaba achieved dentro de la ventana de 14 días. Esto causaba que en la UI M1 apareciera como achieved (check verde) pero sin status (UNPAID/PAID/etc) porque no existía claim.

## Causa Raíz

En `ops.v_claims_payment_status_cabinet.sql`, la vista estaba usando `ops.v_cabinet_milestones_achieved_from_trips` para validar achieved, cuando debería usar `ops.v_cabinet_milestones_achieved_from_payment_calc` (vista canónica según los comentarios de la vista).

**Problemas específicos:**
1. **Vista incorrecta**: Usaba `v_cabinet_milestones_achieved_from_trips` en lugar de `v_cabinet_milestones_achieved_from_payment_calc`
2. **Falta de catálogo de montos**: El `expected_amount` se calculaba con CASE repetido, sin un catálogo centralizado
3. **Ventana de 14 días**: No se validaba explícitamente que `achieved_date` estuviera dentro de la ventana `lead_date` a `lead_date + 14 días`

## Solución Implementada

### 1. Cambio en `v_claims_payment_status_cabinet.sql`

**Antes:**
```sql
FROM ops.v_payment_calculation pc
INNER JOIN ops.v_cabinet_milestones_achieved_from_trips m
    ON m.driver_id = pc.driver_id
    AND m.milestone_value = pc.milestone_trips
    AND m.achieved_flag = true
WHERE pc.origin_tag = 'cabinet'
    AND pc.rule_scope = 'partner'
    AND pc.milestone_trips IN (1, 5, 25)
    AND pc.milestone_achieved = true
```

**Después:**
```sql
WITH milestone_amounts AS (
    -- Catálogo de montos por milestone (evita repetir lógica)
    SELECT 1 AS milestone_value, 25::numeric(12,2) AS expected_amount
    UNION ALL SELECT 5, 35::numeric(12,2)
    UNION ALL SELECT 25, 100::numeric(12,2)
),
base_claims_raw AS (
    SELECT 
        m.driver_id,
        pc.person_key,
        pc.lead_date,
        m.milestone_value,
        ma.expected_amount
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
    INNER JOIN ops.v_payment_calculation pc
        ON pc.driver_id = m.driver_id
        AND pc.milestone_trips = m.milestone_value
        AND pc.origin_tag = 'cabinet'
        AND pc.rule_scope = 'partner'
        AND pc.milestone_achieved = true
    INNER JOIN milestone_amounts ma
        ON ma.milestone_value = m.milestone_value
    WHERE m.achieved_flag = true
        AND m.milestone_value IN (1, 5, 25)
        AND m.driver_id IS NOT NULL
        -- Ventana de 14 días: achieved_date debe estar dentro de lead_date + 14 días
        AND m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date
        AND m.achieved_date::date >= pc.lead_date
)
```

### 2. Mejoras Implementadas

- ✅ **Vista canónica**: Usa `v_cabinet_milestones_achieved_from_payment_calc` (source-of-truth)
- ✅ **Catálogo de montos**: CTE `milestone_amounts` centraliza los montos (M1=25, M5=35, M25=100)
- ✅ **Ventana explícita**: Valida que `achieved_date` esté entre `lead_date` y `lead_date + 14 días`
- ✅ **Incluye M1**: Ahora M1, M5 y M25 se generan correctamente cuando están achieved

## Archivos Modificados

1. **`backend/sql/ops/v_claims_payment_status_cabinet.sql`**
   - Cambio de `v_cabinet_milestones_achieved_from_trips` a `v_cabinet_milestones_achieved_from_payment_calc`
   - Agregado CTE `milestone_amounts` para catálogo de montos
   - Validación explícita de ventana de 14 días

2. **`backend/scripts/sql/verify_m1_claims_generation.sql`** (nuevo)
   - CHECK 1: Conteo de drivers con M1 achieved en ventana pero sin claim M1 (esperado: 0)
   - CHECK 2: Spot-check 20 drivers con detalles completos
   - CHECK 3: Verificación de duplicados por grano (driver_id + milestone_value)
   - CHECK 4: Verificación de expected_amount por milestone (M1=25, M5=35, M25=100)
   - RESUMEN: Distribución de M1 achieved vs claims

3. **`backend/scripts/sql/apply_m1_claims_fix.sql`** (nuevo)
   - Script de aplicación del fix
   - Verificación básica post-aplicación

## Comandos para Aplicar

### Opción 1: Usando psql directamente

```powershell
# Configurar variables
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"

# Aplicar fix
& $psql $DATABASE_URL -f backend/sql/ops/v_claims_payment_status_cabinet.sql

# Verificar
& $psql $DATABASE_URL -f backend/scripts/sql/verify_m1_claims_generation.sql
```

### Opción 2: Usando docker exec (si aplica)

```bash
docker exec -i <container_name> psql $DATABASE_URL -f backend/sql/ops/v_claims_payment_status_cabinet.sql
docker exec -i <container_name> psql $DATABASE_URL -f backend/scripts/sql/verify_m1_claims_generation.sql
```

## Resultados Esperados de Verificación

### CHECK 1: M1 achieved en ventana sin claim
```
check_name                                    | count_missing_claims | status
----------------------------------------------+---------------------+--------
CHECK 1: M1 achieved en ventana sin claim     | 0                   | ✓ PASS
```

### CHECK 2: Spot-check (primeras 20 filas)
```
check_name                    | driver_id | milestone_value | lead_date | achieved_date | due_date | expected_amount | claim_exists | claim_status | claim_expected_amount
------------------------------+-----------+-----------------+-----------+---------------+----------+-----------------+-------------+--------------+----------------------
CHECK 2: Spot-check...         | ...       | 1               | ...       | ...           | ...      | 25.00           | 1           | not_paid     | 25.00
```

### CHECK 3: Duplicados
```
check_name                    | count_duplicates | status
------------------------------+-----------------+--------
CHECK 3: Duplicados en claims | 0               | ✓ PASS
```

### CHECK 4: Expected amount
```
check_name                    | milestone_value | count_claims | distinct_amounts | min_amount | max_amount | status
------------------------------+-----------------+-------------+-----------------+------------+------------+--------
CHECK 4: Expected amount...   | 1               | ...         | 1               | 25.00      | 25.00      | ✓ PASS
CHECK 4: Expected amount...   | 5               | ...         | 1               | 35.00      | 35.00      | ✓ PASS
CHECK 4: Expected amount...   | 25              | ...         | 1               | 100.00     | 100.00     | ✓ PASS
```

### RESUMEN
```
check_name                    | total_m1_achieved_in_window | total_m1_claims | missing_claims | status
------------------------------+----------------------------+----------------+----------------+--------
RESUMEN: M1 achieved vs claims| ...                        | ...            | 0              | ✓ PASS
```

## Validación Frontend

**No se requieren cambios en frontend** porque:
- `CompactMilestoneCell` ya pinta `achieved_flag` independientemente de si existe claim
- `yango_payment_status` solo se muestra si existe claim (NULL si no existe)
- El fix asegura que M1 tenga claim cuando está achieved, por lo que `yango_payment_status` aparecerá correctamente

## Reglas de Negocio Confirmadas

1. ✅ **Milestones claimables**: 1, 5, 25 para `origin_tag='cabinet'`
2. ✅ **Montos esperados**: M1=25, M5=35, M25=100
3. ✅ **Claims acumulativos**: Si driver logra M1 y luego M5, ambos claims existen
4. ✅ **Ventana de 14 días**: Basada en `lead_date`, `achieved_date` debe estar entre `lead_date` y `lead_date + 14 días`
5. ✅ **Status**: UNPAID si no hay pago, PAID/PAID_MISAPPLIED si hay pago conciliado

## Notas Técnicas

- **Grano de claim**: `(driver_id, milestone_value)` - 1 fila por claim
- **Deduplicación**: `DISTINCT ON (driver_id, milestone_value)` con `lead_date DESC`
- **Source-of-truth achieved**: `ops.v_cabinet_milestones_achieved_from_payment_calc`
- **Source-of-truth payment**: `ops.v_yango_payments_ledger_latest_enriched`

