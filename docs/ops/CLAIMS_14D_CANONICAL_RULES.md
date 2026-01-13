# Reglas Canónicas: Claims Yango Cabinet 14D

**Fecha:** 2026-01-13  
**Estado:** ✅ APROBADAS

---

## Principios Fundamentales

1. **Claims independientes por milestone:** M1, M5, M25 (NO se reemplazan)
2. **Claim existe aunque NO esté pagado:** expected ≠ paid
3. **Ventana 14d estricta:** [lead_date_canónico, lead_date + 14d). Fuera de ventana → no claim
4. **Montos Yango→YEGO:** M1 S/25, M5 S/35, M25 S/100

---

## Reglas de Generación de Claims

### REGLA 1: Un claim 14d DEBE existir si:

- ✅ `driver_id IS NOT NULL`
- ✅ `person_key IS NOT NULL`
- ✅ `milestone_value IN (1, 5, 25)`
- ✅ `milestone alcanzado dentro de ventana 14d` (trips_in_window >= milestone dentro de [lead_date_canonico, lead_date_canonico + 14 days))
- ✅ `lead_date_canonico IS NOT NULL`

### REGLA 2: Un claim 14d NO debe existir si:

- ❌ `milestone NO alcanzado dentro de ventana 14d`
- ❌ `driver_id IS NULL`
- ❌ `person_key IS NULL`
- ❌ `lead_date_canonico IS NULL`

---

## Lead-First: Universo Base

- **Universo:** `public.module_ct_cabinet_leads`
- **lead_date_canonico:** `lead_created_at::date` (mismo que `ops.v_cabinet_leads_limbo`)
- **source_pk canónico:** `COALESCE(external_id::text, id::text)`

---

## Ventana 14d Estricta

- **Definición:** `[lead_date_canonico, lead_date_canonico + INTERVAL '14 days')`
- **Trips se miden con:** `public.summary_daily` (o fuente canónica equivalente)
- **Fuera de ventana:** NO genera claim

---

## Montos por Milestone

| Milestone | Monto (S/) |
|-----------|------------|
| M1 (1 viaje) | 25.00 |
| M5 (5 viajes) | 35.00 |
| M25 (25 viajes) | 100.00 |

**Total acumulativo:** Si alcanza M25, total = 25 + 35 + 100 = S/ 160.00

---

## Estados de Claim

### ENUM: `claimstatus`

- `expected`: Claim debe existir pero aún no generado
- `generated`: Claim generado en tabla física
- `paid`: Claim pagado (paid_at IS NOT NULL)
- `rejected`: Claim rechazado
- `expired`: Claim expirado (fuera de ventana)

---

## Ejemplos

### Ejemplo 1: Claim M1 Generado pero No Pagado

```sql
SELECT 
    claim_id,
    person_key,
    lead_date,
    milestone,
    amount_expected,
    status,
    paid_at
FROM canon.claims_yango_cabinet_14d
WHERE claim_id = 1;
```

**Resultado:**
- status: `'generated'`
- paid_at: `NULL` ✅

**Confirmación:** Claim existe (expected=true) pero NO está pagado. ✅

### Ejemplo 2: Milestone Alcanzado pero Sin Claim

```sql
SELECT 
    lead_id,
    driver_id,
    milestone_value,
    trips_14d,
    milestone_achieved,
    claim_expected,
    claim_exists,
    gap_reason
FROM ops.v_cabinet_claims_gap_14d
WHERE gap_reason = 'CLAIM_NOT_GENERATED'
LIMIT 1;
```

**Resultado esperado:**
- milestone_achieved: `true`
- claim_expected: `true`
- claim_exists: `false`
- gap_reason: `'CLAIM_NOT_GENERATED'` ✅

---

## Fuentes de Verdad

1. **Expected claims:** `ops.v_cabinet_claims_expected_14d`
2. **Gaps:** `ops.v_cabinet_claims_gap_14d`
3. **Claims físicos:** `canon.claims_yango_cabinet_14d`

---

## Notas Importantes

- **Claims NO se basan en pagos.** Pagos solo concilian.
- **Todo auditable:** SQL views + tablas + docs + runbooks + scripts de validación.
- **No DDL mágico en startup:** Alembic para tablas y cambios persistentes.
