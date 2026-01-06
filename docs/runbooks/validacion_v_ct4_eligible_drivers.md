# Validación: Vista CT4 Eligible Drivers

**Fecha:** 2025-01-XX  
**Vista:** `ops.v_ct4_eligible_drivers`

---

## Propósito

La vista `ops.v_ct4_eligible_drivers` define el **universo elegible CT4** de drivers que pueden recibir pagos por milestones. Esta vista combina:

- **Origen del driver** (`origin_tag`): `cabinet` o `fleet_migration`
- **Identidad confirmada** (`person_key` + `identity_status`)
- **Información de matching** (`match_rule`, `match_confidence`)
- **Timestamps** (`first_seen_at`, `latest_snapshot_at`)

---

## Criterios de Elegibilidad

Un driver es elegible si cumple **TODOS** estos criterios:

1. ✅ `origin_tag IN ('cabinet', 'fleet_migration')`
2. ✅ `driver_id IS NOT NULL`
3. ✅ `identity_status IN ('confirmed', 'enriched', NULL)`
   - **NOTA:** `NULL` se permite porque algunos drivers pueden tener `person_key` sin status explícito pero están en el sistema

---

## Queries de Validación

### 1. Conteo Total

```sql
SELECT COUNT(*) AS total_eligible_drivers
FROM ops.v_ct4_eligible_drivers;
```

**Resultado esperado:** Número total de drivers elegibles (ej: ~500-2000 dependiendo del volumen)

---

### 2. Distribución por Origin Tag

```sql
SELECT 
    origin_tag,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
GROUP BY origin_tag
ORDER BY count_drivers DESC;
```

**Resultado esperado:**
- `cabinet`: ~70-90% del total
- `fleet_migration`: ~10-30% del total

**Validación:** Ambos origin_tags deben estar presentes.

---

### 3. Distribución por Identity Status

```sql
SELECT 
    COALESCE(identity_status, 'NULL') AS identity_status,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
GROUP BY identity_status
ORDER BY count_drivers DESC;
```

**Resultado esperado:**
- `confirmed`: ~50-70% (drivers con identidad upstream)
- `enriched`: ~20-40% (drivers con matching por nombre único)
- `NULL`: ~5-15% (drivers sin status explícito pero elegibles)

**Validación:** La mayoría debería tener `confirmed` o `enriched`.

---

### 4. Top 20 Drivers Más Recientes

```sql
SELECT 
    driver_id,
    person_key,
    origin_tag,
    identity_status,
    match_rule,
    match_confidence,
    first_seen_at,
    latest_snapshot_at
FROM ops.v_ct4_eligible_drivers
ORDER BY latest_snapshot_at DESC NULLS LAST, first_seen_at DESC NULLS LAST
LIMIT 20;
```

**Validación:**
- `latest_snapshot_at` debe ser reciente (últimos 30 días)
- `first_seen_at` debe ser anterior o igual a `latest_snapshot_at`
- Todos deben tener `origin_tag` válido

---

### 5. Distribución por Match Confidence

```sql
SELECT 
    COALESCE(match_confidence, 'NULL') AS match_confidence,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
GROUP BY match_confidence
ORDER BY 
    CASE match_confidence
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        ELSE 4
    END;
```

**Resultado esperado:**
- `high`: ~50-70% (mayoría con alta confianza)
- `medium`: ~20-40%
- `low`: ~5-15%
- `NULL`: <5%

---

### 6. Drivers sin Person Key

```sql
SELECT 
    COUNT(*) AS drivers_without_person_key,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers), 0), 2) AS pct_total
FROM ops.v_ct4_eligible_drivers
WHERE person_key IS NULL;
```

**Resultado esperado:** <5% de drivers sin `person_key`

**Validación:** La mayoría debe tener `person_key` (identidad canónica).

---

### 7. Comparación con Driver Matrix

```sql
-- Drivers en matrix pero no elegibles
SELECT 
    'En matrix pero no elegible' AS category,
    COUNT(*) AS count_drivers
FROM ops.v_payments_driver_matrix_cabinet dm
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.v_ct4_eligible_drivers ed
    WHERE ed.driver_id = dm.driver_id
)
UNION ALL
-- Drivers elegibles pero no en matrix
SELECT 
    'Elegible pero no en matrix' AS category,
    COUNT(*) AS count_drivers
FROM ops.v_ct4_eligible_drivers ed
WHERE NOT EXISTS (
    SELECT 1 
    FROM ops.v_payments_driver_matrix_cabinet dm
    WHERE dm.driver_id = ed.driver_id
);
```

**Validación:**
- "En matrix pero no elegible": Debe ser 0 o muy bajo (<1%)
- "Elegible pero no en matrix": Puede ser >0 (drivers sin milestones aún)

---

### 8. Validación de Integridad de Datos

```sql
-- Drivers con first_seen_at > latest_snapshot_at (inconsistencia)
SELECT 
    COUNT(*) AS inconsistent_timestamps
FROM ops.v_ct4_eligible_drivers
WHERE first_seen_at IS NOT NULL 
    AND latest_snapshot_at IS NOT NULL
    AND first_seen_at > latest_snapshot_at;
```

**Resultado esperado:** 0 (no debe haber inconsistencias)

---

### 9. Drivers por Origin Tag y Identity Status

```sql
SELECT 
    origin_tag,
    COALESCE(identity_status, 'NULL') AS identity_status,
    COUNT(*) AS count_drivers
FROM ops.v_ct4_eligible_drivers
GROUP BY origin_tag, identity_status
ORDER BY origin_tag, count_drivers DESC;
```

**Validación:** Debe haber drivers en todas las combinaciones válidas.

---

## Checklist de Validación

Antes de usar la vista en producción, verificar:

- [ ] ✅ Conteo total > 0
- [ ] ✅ Ambos origin_tags presentes (`cabinet`, `fleet_migration`)
- [ ] ✅ Mayoría con `identity_status = 'confirmed'` o `'enriched'`
- [ ] ✅ <5% sin `person_key`
- [ ] ✅ <1% "En matrix pero no elegible"
- [ ] ✅ 0 inconsistencias de timestamps
- [ ] ✅ Top 20 drivers con `latest_snapshot_at` reciente

---

## Uso de la Vista

### Filtrar ACHIEVED

```sql
SELECT *
FROM ops.v_cabinet_milestones_achieved_from_trips a
INNER JOIN ops.v_ct4_eligible_drivers ed
    ON ed.driver_id = a.driver_id;
```

### Filtrar PAID

```sql
SELECT *
FROM ops.v_cabinet_milestones_paid p
INNER JOIN ops.v_ct4_eligible_drivers ed
    ON ed.driver_id = p.driver_id;
```

### Filtrar RECONCILED

```sql
SELECT *
FROM ops.v_cabinet_milestones_reconciled r
INNER JOIN ops.v_ct4_eligible_drivers ed
    ON ed.driver_id = r.driver_id;
```

---

## Troubleshooting

### Problema: Vista vacía

**Causa posible:** No hay drivers con `origin_tag IN ('cabinet', 'fleet_migration')`

**Solución:** Verificar `observational.v_conversion_metrics`:

```sql
SELECT origin_tag, COUNT(*) 
FROM observational.v_conversion_metrics 
WHERE origin_tag IN ('cabinet', 'fleet_migration')
GROUP BY origin_tag;
```

### Problema: Muchos drivers sin person_key

**Causa posible:** Drivers sin identidad confirmada en `canon.identity_links`

**Solución:** Verificar matching de identidad:

```sql
SELECT COUNT(*) 
FROM canon.identity_links 
WHERE source_table = 'drivers';
```

### Problema: Inconsistencias con driver_matrix

**Causa posible:** Drivers en matrix con origin_tag diferente o sin identidad

**Solución:** Comparar directamente:

```sql
SELECT dm.driver_id, dm.origin_tag, ed.origin_tag, ed.identity_status
FROM ops.v_payments_driver_matrix_cabinet dm
LEFT JOIN ops.v_ct4_eligible_drivers ed ON ed.driver_id = dm.driver_id
WHERE dm.origin_tag IS DISTINCT FROM ed.origin_tag
LIMIT 10;
```

---

## Referencias

- **Vista SQL:** `backend/sql/ops/v_ct4_eligible_drivers.sql`
- **Fuentes canónicas:**
  - `observational.v_conversion_metrics` (origin_tag)
  - `canon.identity_links` (person_key, identity)
  - `ops.v_yango_payments_ledger_latest_enriched` (identity_status)





