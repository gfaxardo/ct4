# LEAD_DATE_CANONICO - Definición Congelada

**Fecha de congelación:** 2026-01-13  
**Estado:** ✅ CONGELADO

---

## Definición Canónica

**LEAD_DATE_CANONICO = `lead_created_at::date`**

- **Tabla fuente:** `public.module_ct_cabinet_leads`
- **Campo RAW:** `lead_created_at` (timestamp)
- **Conversión:** `lead_created_at::date` (extrae solo la fecha, sin hora)
- **Propósito:** Fecha cero operativa del lead (fecha real del archivo/import, NO timestamp de inserción en BD)

---

## Reglas de Uso

1. **NO usar `created_at`** (timestamp de inserción en BD)
2. **NO usar otra fecha** (ej: `last_active_date`, `activation_date`)
3. **Siempre convertir a date:** `lead_created_at::date`
4. **Validar NOT NULL:** `WHERE lead_created_at IS NOT NULL`

---

## Uso en Vistas

### ✅ Correcto (v_cabinet_leads_limbo)

```sql
mcl.lead_created_at::date AS lead_date
```

### ✅ Correcto (v_cabinet_claims_expected_14d)

```sql
mcl.lead_created_at::date AS lead_date_canonico
```

### ✅ Correcto (week_start)

```sql
DATE_TRUNC('week', mcl.lead_created_at::date)::date AS week_start
```

---

## Validación SQL

```sql
-- Verificar que todos los leads tienen lead_created_at
SELECT 
    COUNT(*) AS total_leads,
    COUNT(lead_created_at) AS leads_with_date,
    COUNT(*) - COUNT(lead_created_at) AS leads_without_date
FROM public.module_ct_cabinet_leads;

-- Verificar rango de fechas
SELECT 
    MIN(lead_created_at::date) AS min_date,
    MAX(lead_created_at::date) AS max_date,
    COUNT(*) AS total
FROM public.module_ct_cabinet_leads
WHERE lead_created_at IS NOT NULL;

-- Verificar leads post-05/01/2026
SELECT COUNT(*) 
FROM public.module_ct_cabinet_leads 
WHERE lead_created_at::date > '2026-01-05';
```

---

## Notas

- Esta definición es la fuente de verdad para todas las vistas operativas
- Cualquier cambio debe documentarse y actualizar todas las vistas afectadas
- NO cambiar sin aprobación explícita
