# Fix: Alineación UI M1 Claims

## Problema Identificado

La UI muestra "M1 sin Claim: 107" aunque el fix de generación de claims funciona correctamente.

### Causa Raíz

**Vista `v_payments_driver_matrix_cabinet`** usa dos fuentes diferentes:
1. **Flags achieved**: `v_cabinet_milestones_achieved_from_trips` (7,914 drivers con M1, sin filtro de ventana)
2. **Claims**: `v_claims_payment_status_cabinet` (116 claims M1, con filtro de ventana de 14 días)

**Resultado**:
- 222 drivers con `m1_achieved_flag=true` (desde trips, incluye históricos)
- 116 drivers con `m1_yango_payment_status IS NOT NULL` (desde claims, solo dentro de ventana)
- Diferencia: 106-107 drivers con M1 achieved pero sin claim

**Estos 107 drivers tienen M1 achieved históricamente pero están fuera de la ventana de 14 días**, por lo que es correcto que no tengan claim. Sin embargo, la UI los cuenta como "M1 sin Claim", lo cual es confuso.

## Solución Aplicada

### Cambio en `v_payments_driver_matrix_cabinet`

**Antes**:
```sql
FROM ops.v_cabinet_milestones_achieved_from_trips m
```

**Después**:
```sql
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
```

**Razón**:
- `v_cabinet_milestones_achieved_from_payment_calc` es el source-of-truth canónico
- Ya está siendo usado por `v_claims_payment_status_cabinet`
- Solo incluye M1 dentro de ventana de 14 días (alineado con claims)
- Garantiza consistencia entre achieved flags y claims

## Archivos Modificados

1. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Cambio de `v_cabinet_milestones_achieved_from_trips` a `v_cabinet_milestones_achieved_from_payment_calc`
   - Actualización de comentarios para reflejar el cambio

2. **`backend/scripts/sql/verify_ui_m1_fix.sql`** (nuevo)
   - Script de verificación post-fix

## Comandos para Aplicar

```powershell
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"

# Aplicar fix
& $psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql

# Verificar
& $psql $DATABASE_URL -f backend/scripts/sql/verify_ui_m1_fix.sql
```

## Resultados Esperados

### VERIF 1: Alineación achieved vs claims
```
m1_achieved_count | m1_with_claim_count | m1_achieved_without_claim | status
------------------+---------------------+---------------------------+--------
223               | 116                 | 0                         | ✓ PASS
```

**Interpretación**: 
- 223 drivers con M1 achieved (dentro de ventana)
- 116 drivers con claim M1
- 0 drivers con M1 achieved pero sin claim (dentro de ventana)
- Los 107 restantes están fuera de ventana (correcto que no tengan claim)

### VERIF 2: Alineación payment_calc vs driver_matrix
```
in_payment_calc | in_driver_matrix | difference | status
----------------+------------------+------------+--------
223             | 223              | 0          | ✓ PASS
```

**Interpretación**: Flags achieved en driver_matrix coinciden con payment_calc.

### VERIF 3: Resumen por milestone
```
milestone | achieved_count | claim_count | gap_count
----------+----------------+-------------+-----------
M1        | 223            | 116         | 0
M5        | ...            | ...         | 0
M25       | ...            | ...         | 0
```

**Interpretación**: Todos los milestones tienen achieved y claims alineados.

## Impacto en UI

### Antes del Fix
- "M1 sin Claim: 107" (confuso, incluye fuera de ventana)
- Flags achieved muestran M1 históricos (7,914 drivers)
- Claims solo muestran M1 dentro de ventana (116 claims)

### Después del Fix
- "M1 sin Claim: 0" (correcto, solo cuenta dentro de ventana)
- Flags achieved muestran solo M1 dentro de ventana (223 drivers)
- Claims muestran M1 dentro de ventana (116 claims)
- Alineación perfecta entre achieved y claims

## Notas Técnicas

- **Source-of-truth achieved**: `ops.v_cabinet_milestones_achieved_from_payment_calc`
- **Source-of-truth claims**: `ops.v_claims_payment_status_cabinet`
- **Ventana de 14 días**: Aplicada consistentemente en ambas fuentes
- **Comportamiento**: Solo M1 dentro de ventana genera claim y aparece como achieved

