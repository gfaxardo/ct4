# Componentes de Pagos Yango

## Componentes Creados

### 1. YangoDashboard.tsx
Dashboard semanal con:
- KPIs totales: Total Expected, Total Paid, Total Diff, Total Anomalías
- Tabla semanal con métricas por semana
- Click en semana abre drilldown

### 2. YangoWeekDrilldown.tsx
Modal de drilldown por semana con:
- Tabs: Resumen | Anomalías | Pendientes | Pagados
- Filtros: búsqueda por driver, motivo, milestone, match confidence
- Export CSV
- Paginación (excepto en tab Resumen)

### 3. Utils

#### utils/reasons.ts
Función `computeAnomalyReason()` que calcula motivos de anomalías:
- `NO_EXPECTED_NO_LEAD_DATE`: Sin expected y sin lead_date
- `NO_EXPECTED_HAS_LEAD_DATE`: Sin expected pero con lead_date
- `PAID_MATCH_NONE`: Pago sin match (alta prioridad)
- `EXPECTED_PENDING_NOT_PAID`: Expected pendiente sin pago
- `PAID`: Pagado
- `UNKNOWN`: Desconocido

#### utils/csv.ts
Función `exportToCSV()` para exportar datos a CSV localmente.

## Cómo Probar

1. **Navegar a `/pagos`**
2. **Click en tab "Yango"**
3. **Verificar dashboard semanal:**
   - Debe mostrar KPIs en la parte superior
   - Tabla con semanas y métricas
4. **Click en una semana:**
   - Debe abrir modal con drilldown
5. **Probar tabs en drilldown:**
   - Resumen: muestra todos los items (limitado a 200)
   - Anomalías: solo items con status 'anomaly_paid_without_expected'
   - Pendientes: solo items con status 'pending'
   - Pagados: solo items con status 'paid'
6. **Probar filtros:**
   - Búsqueda por driver name
   - Filtro por motivo (solo en tab Anomalías)
   - Filtro por milestone
   - Filtro por match confidence
7. **Probar export CSV:**
   - Click en "Exportar CSV"
   - Debe descargar archivo con datos filtrados
8. **Verificar que tab Scouts sigue funcionando:**
   - Cambiar a tab Scouts
   - Verificar que no se rompió nada

## Endpoints Utilizados

- `GET /api/v1/yango/payments/reconciliation/summary` - Resumen agregado
- `GET /api/v1/yango/payments/reconciliation/items` - Items detallados

## Notas

- Los motivos se calculan en frontend usando `computeAnomalyReason()`
- El export CSV es completamente local (sin backend)
- El dashboard agrega datos por semana desde el summary
- El drilldown carga todos los items de la semana para permitir filtros locales


