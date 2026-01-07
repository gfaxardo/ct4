# Driver Matrix SQL - Auditoría y Comparación

## Resumen Ejecutivo

Este documento compara 3 archivos SQL relacionados con la vista `ops.v_payments_driver_matrix_cabinet` para determinar cuál debe ser la versión canónica.

**Archivos analizados:**
1. `backend/sql/ops/v_payments_driver_matrix_cabinet.sql` (456 líneas) - **Versión principal actual**
2. `backend/sql/ops/v_payments_driver_matrix_cabinet_corrected.sql` (166 líneas) - **Versión "corrected"**
3. `backend/sql/ops/v_payments_driver_matrix_cabinet_verification.sql` (234 líneas) - **Solo queries de verificación**

---

## 1. Diferencias Funcionales

### 1.1 Flags de Inconsistencia de Milestones

**v_payments_driver_matrix_cabinet.sql (principal):**
- ✅ **INCLUYE** 3 campos nuevos:
  - `m5_without_m1_flag boolean`
  - `m25_without_m5_flag boolean`
  - `milestone_inconsistency_notes text`
- Lógica: Detecta cuando un milestone superior tiene `achieved_flag=true` pero el anterior no.

**v_payments_driver_matrix_cabinet_corrected.sql:**
- ❌ **NO INCLUYE** flags de inconsistencia
- Solo tiene los campos estándar de milestones.

**Impacto:** La versión principal tiene funcionalidad adicional que la versión corrected no tiene.

---

### 1.2 Función para `achieved_flag`

**v_payments_driver_matrix_cabinet.sql (principal):**
```sql
MAX(CASE WHEN bc.milestone_value = 1 THEN true ELSE false END) AS m1_achieved_flag
```

**v_payments_driver_matrix_cabinet_corrected.sql:**
```sql
BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag
```

**Diferencia funcional:**
- `MAX(CASE ... THEN true ELSE false END)`: Siempre devuelve `true` o `false`, nunca NULL. Si no hay registros, devuelve `false`.
- `BOOL_OR(...)`: Devuelve `true` si al menos un registro cumple la condición, `false` si ninguno cumple, o `NULL` si no hay registros en el grupo.

**Impacto:** `BOOL_OR` es más eficiente y semánticamente correcto para flags booleanos, pero puede devolver NULL si no hay registros (aunque en este caso con GROUP BY siempre habrá al menos un registro).

---

### 1.3 Manejo de `person_key`

**v_payments_driver_matrix_cabinet.sql (principal):**
```sql
MAX(bc.person_key) AS person_key
```

**v_payments_driver_matrix_cabinet_corrected.sql:**
```sql
(array_agg(bc.person_key ORDER BY bc.lead_date DESC NULLS LAST))[1] AS person_key
```

**Diferencia funcional:**
- `MAX(bc.person_key)`: Selecciona el person_key "máximo" (orden lexicográfico para UUIDs, que es arbitrario).
- `array_agg(...)[1]`: Selecciona el person_key del registro con la `lead_date` más reciente, que es más semánticamente correcto.

**Impacto:** La versión corrected es más precisa al seleccionar el `person_key` del milestone más reciente.

---

### 1.4 DROP VIEW Statement

**v_payments_driver_matrix_cabinet.sql (principal):**
- ❌ **NO INCLUYE** `DROP VIEW IF EXISTS`
- Usa `CREATE OR REPLACE VIEW`

**v_payments_driver_matrix_cabinet_corrected.sql:**
- ✅ **INCLUYE** `DROP VIEW IF EXISTS ops.v_payments_driver_matrix_cabinet CASCADE;`
- Luego usa `CREATE VIEW` (no `CREATE OR REPLACE`)

**Impacto:** El `DROP ... CASCADE` puede romper dependencias si hay otras vistas/objetos que dependen de esta vista. `CREATE OR REPLACE` es más seguro.

---

### 1.5 Comentarios y Documentación

**v_payments_driver_matrix_cabinet.sql (principal):**
- ✅ **INCLUYE** comentarios extensos:
  - Propósito de negocio
  - Reglas de negocio
  - Dependencias
  - `COMMENT ON VIEW` y `COMMENT ON COLUMN` para todas las columnas
  - Queries de verificación comentadas al final

**v_payments_driver_matrix_cabinet_corrected.sql:**
- ❌ **NO INCLUYE** comentarios extensos
- Solo comentarios mínimos inline

**Impacto:** La versión principal tiene mejor documentación, lo cual es importante para mantenibilidad.

---

## 2. Dependencias (Objetos Consumidos)

### 2.1 v_payments_driver_matrix_cabinet.sql (principal)

**CTEs y fuentes:**
1. `ops.v_claims_payment_status_cabinet` - Claims base con milestones
2. `ops.v_yango_cabinet_claims_for_collection` - `yango_payment_status`
3. `ops.v_yango_payments_claims_cabinet_14d` - `window_status`
4. `ops.v_payment_calculation` - `origin_tag`
5. `public.drivers` - `driver_name` (full_name)

**Total: 5 dependencias**

### 2.2 v_payments_driver_matrix_cabinet_corrected.sql

**CTEs y fuentes:**
1. `ops.v_claims_payment_status_cabinet` - Claims base con milestones
2. `ops.v_yango_cabinet_claims_for_collection` - `yango_payment_status`
3. `ops.v_yango_payments_claims_cabinet_14d` - `window_status`
4. `ops.v_payment_calculation` - `origin_tag`
5. `public.drivers` - `driver_name` (full_name)

**Total: 5 dependencias (iguales)**

**Conclusión:** Ambas versiones tienen las mismas dependencias.

---

## 3. Columnas Expuestas

### 3.1 Columnas Comunes (ambas versiones)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `driver_id` | text | ID del conductor (grano principal) |
| `person_key` | uuid | Person key (identidad canónica) |
| `driver_name` | text | Nombre del conductor |
| `lead_date` | date | Primera lead_date entre todos los milestones |
| `week_start` | date | Lunes de la semana de lead_date |
| `origin_tag` | text | 'cabinet' o 'fleet_migration' |
| `connected_flag` | boolean | Flag de conexión (siempre false por ahora) |
| `connected_date` | date | Fecha de conexión (siempre NULL por ahora) |

**Milestone M1:**
- `m1_achieved_flag` (boolean)
- `m1_achieved_date` (date)
- `m1_expected_amount_yango` (numeric)
- `m1_yango_payment_status` (text)
- `m1_window_status` (text)
- `m1_overdue_days` (integer)

**Milestone M5:**
- `m5_achieved_flag` (boolean)
- `m5_achieved_date` (date)
- `m5_expected_amount_yango` (numeric)
- `m5_yango_payment_status` (text)
- `m5_window_status` (text)
- `m5_overdue_days` (integer)

**Milestone M25:**
- `m25_achieved_flag` (boolean)
- `m25_achieved_date` (date)
- `m25_expected_amount_yango` (numeric)
- `m25_yango_payment_status` (text)
- `m25_window_status` (text)
- `m25_overdue_days` (integer)

**Scout:**
- `scout_due_flag` (boolean, siempre NULL)
- `scout_paid_flag` (boolean, siempre NULL)
- `scout_amount` (numeric, siempre NULL)

**Total columnas comunes: 31**

### 3.2 Columnas Adicionales (solo versión principal)

**v_payments_driver_matrix_cabinet.sql (principal):**
- ✅ `m5_without_m1_flag` (boolean)
- ✅ `m25_without_m5_flag` (boolean)
- ✅ `milestone_inconsistency_notes` (text)

**Total columnas versión principal: 34**

**v_payments_driver_matrix_cabinet_corrected.sql:**
- ❌ No tiene estas 3 columnas

**Total columnas versión corrected: 31**

---

## 4. Riesgos (Breaking Changes)

### 4.1 Si elegimos v_payments_driver_matrix_cabinet.sql (principal) como canónico

**Riesgos:**
- ✅ **Bajo riesgo**: Es la versión actualmente en uso
- ✅ **Incluye flags de inconsistencia** que ya están implementados en frontend/backend
- ⚠️ **Uso de MAX(CASE ...)** es menos eficiente que BOOL_OR pero funcionalmente equivalente
- ⚠️ **MAX(person_key)** puede seleccionar un person_key arbitrario en lugar del más reciente

**Breaking changes si cambiamos a corrected:**
- ❌ **ALTO RIESGO**: Se perderían 3 columnas (`m5_without_m1_flag`, `m25_without_m5_flag`, `milestone_inconsistency_notes`)
- ❌ El frontend/backend que ya consume estas columnas fallaría
- ❌ El endpoint `/api/v1/ops/payments/driver-matrix` retornaría errores de validación

### 4.2 Si elegimos v_payments_driver_matrix_cabinet_corrected.sql como canónico

**Riesgos:**
- ❌ **ALTO RIESGO**: Falta funcionalidad (flags de inconsistencia)
- ❌ **Breaking change**: Se perderían 3 columnas que ya están en producción
- ✅ **Mejoras técnicas**: BOOL_OR más eficiente, array_agg más preciso para person_key
- ⚠️ **DROP ... CASCADE**: Puede romper dependencias si hay otras vistas que dependen de esta

**Breaking changes:**
- ❌ Frontend mostraría errores al intentar acceder a `m5_without_m1_flag`, etc.
- ❌ Backend schema validation fallaría
- ❌ Cualquier script/reporte que use estas columnas fallaría

### 4.3 Si elegimos v_payments_driver_matrix_cabinet_verification.sql

**Riesgos:**
- ❌ **NO APLICA**: Este archivo NO define la vista, solo contiene queries de verificación
- ✅ Puede usarse como complemento para validar cualquier versión

---

## 5. Recomendación

### ✅ **RECOMENDACIÓN: Usar v_payments_driver_matrix_cabinet.sql (principal) como canónico**

**Razones:**

1. **Funcionalidad completa:**
   - Incluye los flags de inconsistencia (`m5_without_m1_flag`, `m25_without_m5_flag`, `milestone_inconsistency_notes`) que ya están implementados y en uso.

2. **Sin breaking changes:**
   - Es la versión actualmente en producción
   - El frontend y backend ya dependen de las 34 columnas

3. **Mejor documentación:**
   - Comentarios extensos que explican propósito, reglas de negocio y dependencias
   - `COMMENT ON VIEW` y `COMMENT ON COLUMN` para todas las columnas

4. **Mejor para deployment:**
   - Usa `CREATE OR REPLACE VIEW` en lugar de `DROP ... CASCADE`, que es más seguro

**Mejoras sugeridas (sin breaking changes):**

1. **Reemplazar MAX(CASE ...) por BOOL_OR para achieved_flags:**
   ```sql
   -- Cambiar de:
   MAX(CASE WHEN bc.milestone_value = 1 THEN true ELSE false END) AS m1_achieved_flag
   -- A:
   BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag
   ```
   - Más eficiente
   - Semánticamente más correcto
   - Funcionalmente equivalente (ambos devuelven boolean)

2. **Mejorar selección de person_key:**
   ```sql
   -- Cambiar de:
   MAX(bc.person_key) AS person_key
   -- A:
   (array_agg(bc.person_key ORDER BY bc.lead_date DESC NULLS LAST))[1] AS person_key
   ```
   - Más preciso (selecciona el person_key del milestone más reciente)
   - Funcionalmente compatible (sigue siendo un UUID)

3. **Mantener flags de inconsistencia:**
   - Ya están implementados y en uso
   - No remover

---

## 6. Plan de Acción Sugerido

### Fase 1: Canonizar versión principal (sin cambios)
1. ✅ Confirmar que `v_payments_driver_matrix_cabinet.sql` es la versión canónica
2. ✅ Documentar que `v_payments_driver_matrix_cabinet_corrected.sql` es una versión alternativa con mejoras técnicas pero sin funcionalidad completa

### Fase 2: Aplicar mejoras técnicas (opcional, sin breaking changes)
1. Reemplazar `MAX(CASE ...)` por `BOOL_OR` para achieved_flags
2. Mejorar selección de `person_key` con `array_agg`
3. Mantener todas las columnas existentes (incluyendo flags de inconsistencia)
4. Validar que no hay cambios funcionales con queries de verificación

### Fase 3: Limpieza (opcional)
1. Considerar renombrar `v_payments_driver_matrix_cabinet_corrected.sql` a `v_payments_driver_matrix_cabinet_alternative.sql` o moverlo a una carpeta de "alternativas"
2. Mantener `v_payments_driver_matrix_cabinet_verification.sql` como herramienta de validación

---

## 7. Tabla Comparativa Resumen

| Aspecto | Principal | Corrected | Verification |
|---------|-----------|----------|--------------|
| **Define la vista** | ✅ Sí | ✅ Sí | ❌ No (solo queries) |
| **Flags inconsistencia** | ✅ Sí (3 campos) | ❌ No | N/A |
| **Total columnas** | 34 | 31 | N/A |
| **BOOL_OR vs MAX(CASE)** | MAX(CASE) | BOOL_OR | N/A |
| **person_key selection** | MAX() | array_agg | N/A |
| **DROP CASCADE** | ❌ No | ✅ Sí | N/A |
| **Documentación** | ✅ Extensa | ❌ Mínima | N/A |
| **En producción** | ✅ Sí | ❌ No | N/A |
| **Breaking changes si adopto** | Ninguno | ❌ Alto (pierde 3 columnas) | N/A |

---

## 8. Conclusión

**Versión canónica recomendada:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`

**Justificación:**
- Funcionalidad completa (incluye flags de inconsistencia)
- Sin breaking changes
- Ya está en producción
- Mejor documentación
- Puede mejorarse técnicamente sin perder funcionalidad

**Archivo corrected:**
- Tiene mejoras técnicas (BOOL_OR, array_agg) pero falta funcionalidad crítica
- Puede usarse como referencia para mejoras futuras
- NO debe reemplazar la versión principal sin antes agregar los flags de inconsistencia

**Archivo verification:**
- Útil como herramienta de validación
- Puede usarse con cualquier versión de la vista
- Mantener como complemento







