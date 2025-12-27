# Fix Upstream: Identidad en module_ct_cabinet_payments

## Objetivo

Agregar columnas `driver_id` y `person_key` a `public.module_ct_cabinet_payments` y poblarlas en el punto de inserción/ingesta upstream. Esto permite que la identidad se propague correctamente al ledger sin depender de matching por nombre.

## Cambios Realizados

### 1. Migración de Base de Datos

**Archivo**: `backend/alembic/versions/012_add_identity_to_cabinet_payments.py`

- Agrega columnas `driver_id` (String, nullable) y `person_key` (UUID, nullable) a `public.module_ct_cabinet_payments`
- Crea índices parciales para mejorar performance
- Agrega comentarios explicativos

**Ejecutar migración**:
```bash
alembic upgrade head
```

O directamente en pgAdmin:
```sql
ALTER TABLE public.module_ct_cabinet_payments 
ADD COLUMN driver_id TEXT,
ADD COLUMN person_key UUID;

CREATE INDEX idx_cabinet_payments_driver_id 
ON public.module_ct_cabinet_payments (driver_id) 
WHERE driver_id IS NOT NULL;

CREATE INDEX idx_cabinet_payments_person_key 
ON public.module_ct_cabinet_payments (person_key) 
WHERE person_key IS NOT NULL;
```

### 2. Vista Raw Actualizada

**Archivo**: `backend/sql/ops/v_yango_payments_raw_current.sql`

- Lee `driver_id` y `person_key` directamente desde `module_ct_cabinet_payments`
- Usa estas columnas como **PRIORIDAD** para identidad
- Matching por nombre solo como **FALLBACK INFORMATIVO** cuando las columnas están NULL
- `match_rule`: `'source_upstream'` si viene de columnas, `'driver_name_unique_fallback'` si es fallback
- `match_confidence`: `'high'` si viene de upstream, `'medium'` si es fallback

### 3. Vista Enriquecida Ajustada

**Archivo**: `backend/sql/ops/v_yango_payments_ledger_latest_enriched.sql`

- Respeta la identidad que viene desde `ledger_latest` (que hereda de `raw_current`)
- Solo aplica matching por nombre como fallback cuando `driver_id_original` y `person_key_original` son NULL
- Mantiene reglas SAFE para el fallback informativo

## Punto de Inserción/Ingesta Upstream

### Requerimiento

El proceso que inserta registros en `public.module_ct_cabinet_payments` **DEBE** poblarse las columnas `driver_id` y/o `person_key` cuando estén disponibles.

### Opciones para Poblar

#### Opción A: Si hay relación con leads
Si `module_ct_cabinet_payments` tiene relación con `module_ct_cabinet_leads` (ej: por `external_id` o similar):

```sql
-- Ejemplo: actualizar pagos basándose en leads
UPDATE public.module_ct_cabinet_payments p
SET 
    person_key = le.person_key,
    driver_id = (
        SELECT il.source_pk 
        FROM canon.identity_links il
        WHERE il.person_key = le.person_key 
        AND il.source_table = 'drivers'
        LIMIT 1
    )
FROM public.module_ct_cabinet_leads l
INNER JOIN observational.lead_events le
    ON le.source_table = 'module_ct_cabinet_leads'
    AND le.source_pk = l.external_id::text
WHERE p.external_id = l.external_id  -- Ajustar según relación real
    AND (p.driver_id IS NULL OR p.person_key IS NULL);
```

#### Opción B: Si hay relación con drivers directa
Si el proceso upstream conoce el `driver_id`:

```sql
-- Ejemplo: actualizar desde una tabla de mapping
UPDATE public.module_ct_cabinet_payments p
SET 
    driver_id = m.driver_id,
    person_key = (
        SELECT il.person_key
        FROM canon.identity_links il
        WHERE il.source_table = 'drivers'
        AND il.source_pk = m.driver_id::text
        LIMIT 1
    )
FROM mapping_table m  -- Ajustar según tabla real
WHERE p.some_key = m.some_key  -- Ajustar según relación
    AND (p.driver_id IS NULL OR p.person_key IS NULL);
```

#### Opción C: Población en el INSERT
Si el proceso que inserta puede obtener la identidad en el momento de inserción:

```python
# Ejemplo en código Python (ajustar según implementación real)
def insert_cabinet_payment(db, payment_data):
    # Obtener person_key/driver_id desde donde corresponda
    person_key = get_person_key_for_lead(payment_data['external_id'])
    driver_id = get_driver_id_for_person(person_key)
    
    payment = {
        **payment_data,
        'driver_id': driver_id,  # <-- Agregar aquí
        'person_key': person_key  # <-- Agregar aquí
    }
    
    db.execute(
        insert(ModuleCtCabinetPayments).values(**payment)
    )
```

### Validación de Población

```sql
-- Verificar cuántos registros tienen identidad
SELECT 
    COUNT(*) AS total,
    COUNT(driver_id) AS with_driver_id,
    COUNT(person_key) AS with_person_key,
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL OR person_key IS NOT NULL) AS with_any_identity,
    COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) AS without_identity
FROM public.module_ct_cabinet_payments;

-- Verificar que después de población, el ledger hereda la identidad
SELECT 
    COUNT(*) AS total_ledger,
    COUNT(driver_id) AS with_driver_id,
    COUNT(person_key) AS with_person_key
FROM ops.v_yango_payments_ledger_latest;
```

## Flujo Completo

1. **Upstream inserta** en `module_ct_cabinet_payments` con `driver_id`/`person_key` poblados
2. **v_yango_payments_raw_current** lee esas columnas y las usa como PRIORIDAD
3. **ingest_yango_payments_snapshot** propaga identidad al ledger
4. **v_yango_payments_ledger_latest** expone la identidad original
5. **v_yango_payments_ledger_latest_enriched** solo aplica fallback si original es NULL
6. **v_yango_payments_claims_cabinet_14d** usa identidad final para matching

## Beneficios

- ✅ Identidad confiable desde la fuente
- ✅ No depende de matching por nombre (solo fallback informativo)
- ✅ Mejor performance (índices en columnas)
- ✅ Trazabilidad clara (identity_source indica source)
- ✅ Compatible con datos históricos (columnas nullable)

## Fallback por Nombre (Informativo)

### ¿Por qué es necesario?

El fallback por nombre es **informativo/auxiliar**, NO reemplaza la solución principal (upstream). Se usa cuando:
- Las columnas `driver_id`/`person_key` en `module_ct_cabinet_payments` están NULL
- Se necesita identificar "pagos probables por nombre" para análisis/limpieza
- Permite distinguir entre "sin match", "ambiguous" (múltiples matches), y "match único"

### ¿Cómo funciona?

**Estrategia determinística (NO fuzzy)**:

1. **Dos llaves de matching**:
   - `name_norm_basic`: Normalización básica (UPPER, sin tildes, espacios colapsados)
   - `name_norm_tokens_sorted`: Tokens ordenados alfabéticamente (permite matching cuando el orden varía)

2. **Reglas de seguridad**:
   - Solo asigna identidad si el match es **ÚNICO** (count=1) en el universo
   - Prioridad: primero intenta `name_norm_basic` único, luego `name_norm_tokens_sorted` único
   - Si hay múltiples matches → marca como `'ambiguous'` (no asigna identidad)

3. **Validaciones SAFE**:
   - Longitud mínima: >= 12 caracteres
   - Mínimo 2 tokens válidos
   - Excluye placeholders: 'na', 'n/a', 'unknown', 'sin nombre', etc.

4. **Campos expuestos**:
   - `match_rule`: `'source_upstream'` | `'name_full_unique'` | `'name_tokens_unique'` | `'ambiguous'` | `'no_match'`
   - `match_confidence`: `'high'` (upstream) | `'medium'` (fallback único) | `'low'` (ambiguous) | `'unknown'` (sin match)
   - `identity_source`: `'original'` (upstream) | `'enriched_by_name'` (fallback) | `'none'`

### ¿Cuenta como "paid real"?

**NO**. El fallback por nombre es **informativo** pero NO marca pagos como `paid_status='paid'`.

- `paid_status='paid'` solo se asigna si `identity_source='original'` (upstream)
- Los matches enriched (`identity_source='enriched_by_name'`) se muestran como "probables" o "requieren confirmación"
- Esto asegura que solo pagos con identidad fuerte (upstream) se consideren pagados

### Funciones SQL

**Archivo**: `backend/sql/ops/functions_normalize_name.sql`

- `ops.normalize_name_basic(text)`: Normalización básica determinística
- `ops.normalize_name_tokens_sorted(text)`: Tokens ordenados alfabéticamente (permite matching con orden invertido)

**Ejemplo**:
```sql
SELECT 
    ops.normalize_name_tokens_sorted('Luis Fabio Quispe Anyosa') AS sorted_1,
    ops.normalize_name_tokens_sorted('Quispe Anyosa Luis Fabio') AS sorted_2;
-- Ambos retornan: 'ANYOSA FABIO LUIS QUISPE' (igual)
```

### Vista Extendida

**Archivo**: `backend/sql/ops/v_driver_name_index_extended.sql`

- Extiende `ops.v_driver_name_index` agregando `full_name_normalized_tokens_sorted`
- Permite matching con ambas llaves desde el universo de identidades

## Notas Importantes

1. **Columnas son NULL por defecto**: Permite migración gradual sin romper datos existentes
2. **Fallback es INFORMATIVO**: Solo para análisis/limpieza, NO marca pagos como paid real
3. **Matching por nombre es DETERMINÍSTICO**: No es fuzzy, solo permite variaciones de orden mediante tokens ordenados
4. **Paid real requiere upstream**: Solo `identity_source='original'` cuenta para `paid_status='paid'`
5. **No afecta datos existentes**: Los registros históricos seguirán funcionando (con fallback informativo si es necesario)

## Checklist de Implementación

- [ ] Ejecutar migración `012_add_identity_to_cabinet_payments`
- [ ] Identificar punto de inserción/ingesta upstream
- [ ] Implementar lógica para poblar `driver_id`/`person_key` en inserción
- [ ] Ejecutar script de backfill para datos históricos (si aplica)
- [ ] Validar que `v_yango_payments_raw_current` usa las columnas correctamente
- [ ] Validar que ledger hereda la identidad
- [ ] Monitorear que `identity_source='original'` aumenta y `identity_source='enriched_by_name'` disminuye

