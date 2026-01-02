# Legacy Import Audit Report

**Fecha de auditoría:** 2025-01-27  
**Objetivo:** Identificar componentes legacy de `components/payments/*` que se importan y su uso en páginas NO PENDING del blueprint.

---

## Resumen Ejecutivo

**Componentes legacy analizados:**
1. `YangoDashboard.tsx`
2. `YangoWeekDrilldown.tsx`
3. `ClaimsDrilldown.tsx`
4. `DriverTimelineModal.tsx`
5. Otros componentes en `components/payments/*`

**Resultado:** ❌ **NINGUNO de los componentes legacy se importa en páginas NO PENDING**

---

## Componentes Legacy Identificados

### 1. YangoDashboard.tsx
- **Ruta completa:** `frontend/components/payments/YangoDashboard.tsx`
- **Estado:** Legacy - NO se importa en páginas NO PENDING
- **Importaciones encontradas:** Ninguna en `frontend/app/*`
- **Uso en páginas NO PENDING:** ❌ NO

**Análisis:**
- El componente existe pero NO se importa en ninguna página del blueprint
- La página `/pagos/yango-cabinet` (NO PENDING) implementa su propia UI según el blueprint
- Solo se menciona en `temp_yango_old.tsx` (archivo temporal)

---

### 2. YangoWeekDrilldown.tsx
- **Ruta completa:** `frontend/components/payments/YangoWeekDrilldown.tsx`
- **Estado:** Legacy - NO se importa en páginas NO PENDING
- **Importaciones encontradas:** Ninguna en `frontend/app/*`
- **Uso en páginas NO PENDING:** ❌ NO

**Análisis:**
- Componente legacy para drilldown semanal de Yango
- NO se usa en `/pagos/yango-cabinet` (implementación nueva según blueprint)
- Solo referencias internas dentro del mismo componente

---

### 3. ClaimsDrilldown.tsx
- **Ruta completa:** `frontend/components/payments/ClaimsDrilldown.tsx`
- **Estado:** Legacy - NO se importa (página PENDING)
- **Importaciones encontradas:** Ninguna en `frontend/app/*`
- **Uso en páginas NO PENDING:** ❌ NO
- **Página relacionada:** `/pagos/claims` (PENDING)

**Análisis:**
- Componente para drilldown de claims
- La página `/pagos/claims` está marcada como PENDING en el blueprint
- NO se importa en ninguna página NO PENDING

---

### 4. DriverTimelineModal.tsx
- **Ruta completa:** `frontend/components/payments/DriverTimelineModal.tsx`
- **Estado:** Legacy - NO se importa en páginas NO PENDING
- **Importaciones encontradas:** Ninguna en `frontend/app/*`
- **Uso en páginas NO PENDING:** ❌ NO

**Análisis:**
- Modal para timeline de driver
- NO se usa en ninguna página NO PENDING
- Podría usarse en futuro drilldown de driver, pero actualmente no existe

---

### 5. Otros Componentes en components/payments/

#### ClaimsKPIs.tsx
- **Ruta completa:** `frontend/components/payments/ClaimsKPIs.tsx`
- **Estado:** Legacy - NO se importa
- **Uso en páginas NO PENDING:** ❌ NO

#### DebugPanel.tsx
- **Ruta completa:** `frontend/components/payments/DebugPanel.tsx`
- **Estado:** Legacy - NO se importa
- **Uso en páginas NO PENDING:** ❌ NO

#### utils/ (reasons.ts, week.ts, csv.ts)
- **Rutas:**
  - `frontend/components/payments/utils/reasons.ts`
  - `frontend/components/payments/utils/week.ts`
  - `frontend/components/payments/utils/csv.ts`
- **Estado:** Legacy - Solo usados por componentes legacy
- **Uso en páginas NO PENDING:** ❌ NO

**Análisis:**
- Estos utilities son utilizados por `YangoDashboard.tsx` y `YangoWeekDrilldown.tsx`
- NO se importan directamente desde páginas NO PENDING
- Solo se usan indirectamente a través de componentes legacy

---

## Componentes Adicionales (NO Legacy, pero relacionados)

### WeeklyFilters.tsx
- **Ruta completa:** `frontend/components/WeeklyFilters.tsx`
- **Estado:** Legacy - NO se importa en páginas NO PENDING
- **Importaciones encontradas:** Ninguna en `frontend/app/*`
- **Uso en páginas NO PENDING:** ❌ NO

**Análisis:**
- Componente que existía en la implementación anterior
- La página `/runs` (PENDING) ya no lo importa (fue reemplazada por placeholder)
- NO se usa en páginas NO PENDING

### WeeklyMetricsView.tsx
- **Ruta completa:** `frontend/components/WeeklyMetricsView.tsx`
- **Estado:** Legacy - NO se importa en páginas NO PENDING
- **Importaciones encontradas:** Ninguna en `frontend/app/*`
- **Uso en páginas NO PENDING:** ❌ NO
- **Problema adicional:** Importa tipos desde `@/lib/api` que no existen allí (debería importar desde `@/lib/types`)

**Análisis:**
- Componente que existía en la implementación anterior
- La página `/runs` (PENDING) ya no lo importa (fue reemplazada por placeholder)
- NO se usa en páginas NO PENDING
- Tiene importación incorrecta: `import { WeeklyData, WeeklyTrend } from '@/lib/api'` (tipos no exportados desde api.ts)

---

## Páginas NO PENDING del Blueprint (Verificadas)

Se verificaron todas las páginas NO PENDING según `FRONTEND_UI_BLUEPRINT_v1.md`:

1. ✅ `/dashboard` - `app/dashboard/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/StatCard`, `@/components/Badge`

2. ✅ `/persons` - `app/persons/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/DataTable`, `@/components/Filters`, `@/components/Pagination`, `@/components/Badge`

3. ✅ `/persons/[person_key]` - `app/persons/[person_key]/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/DataTable`, `@/components/Badge`

4. ✅ `/unmatched` - `app/unmatched/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/DataTable`, `@/components/Filters`, `@/components/Pagination`, `@/components/Badge`

5. ✅ `/liquidaciones` - `app/liquidaciones/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/StatCard`, `@/components/DataTable`, `@/components/Filters`, `@/components/Pagination`, `@/components/Badge`

6. ✅ `/pagos` - `app/pagos/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/DataTable`, `@/components/Filters`, `@/components/Pagination`, `@/components/Badge`

7. ✅ `/pagos/yango-cabinet` - `app/pagos/yango-cabinet/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/StatCard`, `@/components/DataTable`, `@/components/Filters`, `@/components/Pagination`, `@/components/Badge`

8. ✅ `/pagos/cobranza-yango` - `app/pagos/cobranza-yango/page.tsx`
   - **Imports legacy:** Ninguno
   - **Imports:** `@/components/StatCard`, `@/components/DataTable`, `@/components/Filters`, `@/components/Pagination`, `@/components/Badge`

**Resultado:** ✅ Todas las páginas NO PENDING usan solo componentes nuevos del blueprint.

---

## Páginas PENDING (Para referencia)

1. `/runs` - `app/runs/page.tsx`
   - **Estado:** PENDING (placeholder)
   - **Imports legacy:** Ninguno (placeholder simple)

2. `/pagos/claims` - `app/pagos/claims/page.tsx`
   - **Estado:** PENDING (placeholder)
   - **Imports legacy:** Ninguno (placeholder simple)

3. `/ops/alerts` - No existe aún
   - **Estado:** PENDING

4. `/ops/data-health` - `app/ops/data-health/page.tsx`
   - **Estado:** PENDING (placeholder)
   - **Imports legacy:** Ninguno (placeholder simple)

---

## Problemas de Compilación

Los componentes legacy causan errores de compilación TypeScript porque:

1. **Tipos incompatibles:** Usan tipos que no coinciden con los del contrato (`YangoReconciliationItemRow` vs `ReconciliationItem`)
2. **Propiedades faltantes:** Referencian propiedades que no existen en los tipos del contrato (`reconciliation_status`, `paid_is_paid`, `paid_raw_driver_name`, etc.)
3. **Funciones no disponibles:** Intentan usar funciones que no están en `lib/api.ts` (`getCabinetPaymentEvidencePack`, `getDriverTimeline`)

**Estado actual:** Se aplicaron workarounds (type casts a `any`) para permitir compilación, pero esto es temporal.

---

## Plan de Cuarentena Recomendado

### Objetivo
Mover componentes legacy a una carpeta de cuarentena y excluirlos del build TypeScript para:
1. Eliminar errores de compilación
2. Preservar código por si se necesita en el futuro
3. Limpiar el proyecto de código no utilizado

### Paso 1: Crear Carpeta de Cuarentena

```
frontend/
  components/
    _legacy/          # Nueva carpeta de cuarentena
      payments/       # Mover components/payments/* aquí
        YangoDashboard.tsx
        YangoWeekDrilldown.tsx
        ClaimsDrilldown.tsx
        DriverTimelineModal.tsx
        ClaimsKPIs.tsx
        DebugPanel.tsx
        utils/
          reasons.ts
          week.ts
          csv.ts
        README.md
        VALIDATION_CHECKLIST.md
```

### Paso 2: Mover Componentes Legacy

**Archivos a mover:**
- `frontend/components/payments/YangoDashboard.tsx` → `frontend/components/_legacy/payments/YangoDashboard.tsx`
- `frontend/components/payments/YangoWeekDrilldown.tsx` → `frontend/components/_legacy/payments/YangoWeekDrilldown.tsx`
- `frontend/components/payments/ClaimsDrilldown.tsx` → `frontend/components/_legacy/payments/ClaimsDrilldown.tsx`
- `frontend/components/payments/DriverTimelineModal.tsx` → `frontend/components/_legacy/payments/DriverTimelineModal.tsx`
- `frontend/components/payments/ClaimsKPIs.tsx` → `frontend/components/_legacy/payments/ClaimsKPIs.tsx`
- `frontend/components/payments/DebugPanel.tsx` → `frontend/components/_legacy/payments/DebugPanel.tsx`
- `frontend/components/payments/utils/*` → `frontend/components/_legacy/payments/utils/*`
- `frontend/components/payments/README.md` → `frontend/components/_legacy/payments/README.md`
- `frontend/components/payments/VALIDATION_CHECKLIST.md` → `frontend/components/_legacy/payments/VALIDATION_CHECKLIST.md`

**Componentes adicionales (fuera de payments/):**
- `frontend/components/WeeklyFilters.tsx` → `frontend/components/_legacy/WeeklyFilters.tsx`
- `frontend/components/WeeklyMetricsView.tsx` → `frontend/components/_legacy/WeeklyMetricsView.tsx`

### Paso 3: Excluir de TypeScript

**Modificar `frontend/tsconfig.json`:**

```json
{
  "compilerOptions": {
    // ... configuración existente
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": [
    "node_modules",
    ".next",
    "components/_legacy/**/*"  // ← Agregar esta línea
  ]
}
```

### Paso 4: Actualizar .gitignore (opcional)

Si se quiere mantener los archivos pero no incluirlos en builds:

```gitignore
# Legacy components (preserved but excluded from build)
components/_legacy/
```

**Nota:** Esto es opcional, ya que TypeScript los excluirá del build.

### Paso 5: Actualizar Next.js Config (si es necesario)

**Modificar `frontend/next.config.js` (si existe):**

```javascript
module.exports = {
  // ... configuración existente
  webpack: (config) => {
    // Excluir componentes legacy del build si es necesario
    config.resolve.alias = {
      ...config.resolve.alias,
    };
    return config;
  },
};
```

**Nota:** TypeScript exclude debería ser suficiente. Solo agregar esto si Next.js intenta incluir los archivos de otra manera.

---

## Comandos para Ejecutar (cuando se apruebe el plan)

```bash
# 1. Crear estructura de cuarentena
mkdir -p frontend/components/_legacy/payments/utils

# 2. Mover componentes legacy
mv frontend/components/payments/* frontend/components/_legacy/payments/

# 3. Mover componentes adicionales
mv frontend/components/WeeklyFilters.tsx frontend/components/_legacy/
mv frontend/components/WeeklyMetricsView.tsx frontend/components/_legacy/

# 4. Eliminar carpeta vacía
rmdir frontend/components/payments  # Solo si está vacía

# 5. Verificar que no hay imports rotos
cd frontend
npm run build
```

---

## Archivos Relacionados que NO son Legacy

Estos archivos SÍ se usan y NO deben moverse:

✅ **Componentes activos:**
- `frontend/components/StatCard.tsx`
- `frontend/components/Badge.tsx`
- `frontend/components/DataTable.tsx`
- `frontend/components/Filters.tsx`
- `frontend/components/Pagination.tsx`
- `frontend/components/Sidebar.tsx`
- `frontend/components/Topbar.tsx`

---

## Recomendaciones Finales

1. ✅ **Proceder con cuarentena:** Los componentes legacy NO se usan en páginas NO PENDING
2. ✅ **Preservar código:** Mover a `_legacy/` permite recuperar código si es necesario
3. ✅ **Limpiar errores:** Excluir de TypeScript eliminará errores de compilación
4. ⚠️ **Revisar antes de eliminar:** Si en el futuro se necesita funcionalidad de estos componentes, revisar `_legacy/` antes de reimplementar

---

## Checklist de Validación

- [x] Audit completado
- [x] Componentes legacy identificados
- [x] Páginas NO PENDING verificadas
- [x] Plan de cuarentena propuesto
- [ ] Plan aprobado por equipo
- [ ] Cuarentena ejecutada
- [ ] Build verificado sin errores
- [ ] Documentación actualizada

---

**Fin del Reporte**

