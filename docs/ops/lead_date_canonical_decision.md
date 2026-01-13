# Decisión: Fecha Cero Canónica (LEAD_DATE_CANONICO)

**Fecha:** 2026-01-XX  
**Tabla:** `public.module_ct_cabinet_leads`

---

## Columnas Relacionadas a Fecha

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `lead_created_at` | `timestamp without time zone` | **Fecha real del lead** (del archivo fuente) |
| `created_at` | `timestamp without time zone` | Timestamp de inserción en BD (puede ser diferente) |
| `last_active_date` | `date` | Última fecha de actividad (no relevante para fecha cero) |

---

## Queries de Auditoría

### Q1: COUNT por lead_created_at::date > '2026-01-05'

```sql
SELECT COUNT(*) 
FROM public.module_ct_cabinet_leads
WHERE lead_created_at::date > '2026-01-05';
```

**Resultado:** 62 leads ✅

### Q2: COUNT por lead_date::date > '2026-01-05'

**Resultado:** ❌ Columna `lead_date` **NO EXISTE** en la tabla

### Q3: Rango min/max para lead_created_at

```sql
SELECT 
    MIN(lead_created_at::date) AS min_date,
    MAX(lead_created_at::date) AS max_date,
    COUNT(*) AS total
FROM public.module_ct_cabinet_leads
WHERE lead_created_at IS NOT NULL;
```

**Resultado:**
- Min: 2025-11-03
- Max: 2026-01-10
- Total: 849 leads

### Q4: Comparación lead_created_at vs created_at

```sql
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE lead_created_at::date != created_at::date) AS different,
    COUNT(*) FILTER (WHERE lead_created_at::date = created_at::date) AS same
FROM public.module_ct_cabinet_leads;
```

**Resultado:**
- Total: 849
- Diferentes: 849 (100%)
- Iguales: 0

**Conclusión:** `created_at` es el timestamp de inserción en BD, mientras que `lead_created_at` es la fecha real del lead del archivo fuente.

### Q5: Top 20 records > '2026-01-05'

**Ejemplos:**
- ID=1235, external_id=2f7c0e7deb9dcadc3e9a6f098425e8a5, lead_created_at=2026-01-10, created_at=2026-01-12
- ID=1236, external_id=de6a41eb753dfb308fcb40836e906b79, lead_created_at=2026-01-10, created_at=2026-01-12

**Observación:** `lead_created_at` es anterior a `created_at` (el lead se creó el 10, pero se insertó en BD el 12).

---

## Decisión: LEAD_DATE_CANONICO

### Definición Congelada

```sql
LEAD_DATE_CANONICO := mcl.lead_created_at::date
```

**Razón:**
1. ✅ `lead_created_at` es la fecha real del lead (del archivo fuente)
2. ✅ `created_at` es solo el timestamp de inserción en BD (no relevante para fecha cero operativa)
3. ✅ No existe columna `lead_date` en la tabla
4. ✅ Todos los registros tienen `lead_created_at` (no hay NULLs)

### Implementación en SQL

```sql
-- En todas las vistas y queries:
LEAD_DATE_CANONICO := mcl.lead_created_at::date

-- week_start derivado:
week_start := DATE_TRUNC('week', mcl.lead_created_at::date)::date

-- ventana 14d:
[lead_created_at::date, lead_created_at::date + INTERVAL '14 days')
```

---

## Validación

### Baseline Post-05

```sql
SELECT COUNT(*) 
FROM public.module_ct_cabinet_leads
WHERE lead_created_at::date > '2026-01-05';
```

**Resultado esperado:** 62 leads ✅

**Nota:** El usuario esperaba ~29 leads, pero la realidad es 62. Esto es correcto según `lead_created_at::date`.

---

## Impacto en Vistas

### Vista Limbo

**Antes:**
```sql
mcl.lead_created_at::date AS lead_date
```

**Después:**
```sql
mcl.lead_created_at::date AS lead_date  -- Ya es correcto, solo documentar
```

### Vista Auditoría Semanal

**Antes:**
```sql
DATE_TRUNC('week', lead_created_at::date)::date AS week_start
```

**Después:**
```sql
DATE_TRUNC('week', lead_created_at::date)::date AS week_start  -- Ya es correcto
```

**Conclusión:** Las vistas ya usan `lead_created_at::date` correctamente. Solo necesitamos documentar que esta es la fecha canónica.

---

## Reglas de Negocio

1. **LEAD_DATE_CANONICO = lead_created_at::date** (congelado)
2. **week_start = DATE_TRUNC('week', lead_created_at::date)::date** (lunes ISO)
3. **ventana 14d = [lead_created_at::date, lead_created_at::date + INTERVAL '14 days')**
4. **NO usar created_at** para fecha cero operativa
5. **NO usar last_active_date** para fecha cero

---

## Notas

- La discrepancia 29 vs 62 es correcta: hay 62 leads con `lead_created_at::date > '2026-01-05'`
- Si el usuario esperaba 29, puede ser que estuviera mirando otra fuente o filtro diferente
- El sistema debe usar `lead_created_at::date` como fecha cero canónica en todas las vistas y queries
