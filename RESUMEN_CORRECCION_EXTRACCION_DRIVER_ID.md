# Resumen: Corrección de Extracción de driver_id en lead_events

**Fecha**: 2025-01-10  
**Estado**: En Progreso - Funcionalidad implementada, requiere validación

## Problema Identificado

El script `fix_drivers_without_leads.py` reportaba:
- Drivers con lead_events: 0
- Drivers sin lead_events: 876

Cuando el dashboard previamente mostraba ~872 drivers con lead_events.

**Causa raíz**: Los eventos en `observational.lead_events` no siempre tienen `driver_id` directo en `payload_json`:
- `module_ct_scouting_daily` (609 eventos): Tienen `driver_license` y `driver_phone`, NO `driver_id`
- `module_ct_migrations` (137 eventos): Tienen `driver_id` directo
- `module_ct_cabinet_leads` (806 eventos): No tienen identificador de driver en payload

## Soluciones Implementadas

### 1. Script de Diagnóstico ✅

Creado `backend/scripts/debug_lead_events_keys.py` que:
- Analiza estructura de `lead_events`
- Identifica keys más comunes en `payload_json`
- Verifica variantes de `driver_id`
- Analiza drivers en cuarentena vs eventos
- Determina patrones de extracción por `source_table`

**Resultados del diagnóstico**:
- Total de lead_events: 1,552
- Solo 137 eventos (8.83%) tienen `driver_id` directo
- 609 eventos (39.24%) tienen `driver_license` y `driver_phone`
- 886 drivers en cuarentena (0% con eventos encontrados con búsqueda simple)

### 2. Función de Extracción Mejorada ✅

Actualizada `find_lead_events_for_driver()` en `fix_drivers_without_leads.py` con múltiples estrategias:

1. **Estrategia 1**: Búsqueda directa por `driver_id` en `payload_json`
   - Busca en: `driver_id`, `driverId`, `id`, `driver.driver_id`, etc.

2. **Estrategia 2**: Búsqueda por `driver_license`/`driver_phone` mapeado a `driver_id`
   - Obtiene `license_norm`/`phone_norm` desde múltiples fuentes:
     - `canon.drivers_index` (prioridad)
     - `public.drivers` con normalización
     - `canon.identity_registry` vía `identity_links`
   - Normaliza valores usando `normalize_license()` y `normalize_phone()`
   - Busca eventos que tengan estos valores normalizados

3. **Estrategia 3**: Búsqueda por `person_key` del driver
   - Si el driver tiene `person_key`, busca eventos con ese `person_key`

### 3. Modo Reproceso ✅

Agregado modo `--reprocess-quarantined` al script que:
- Reprocesa drivers actualmente en cuarentena (`status='quarantined'`)
- Usa la lógica corregida para buscar eventos
- Si encuentra eventos:
  - Crea links faltantes desde `lead_events`
  - Actualiza status a `resolved_relinked`
  - Agrega `resolution_notes` con detalles
- Si no encuentra eventos: deja intacto (mantiene auditabilidad)

### 4. Reportes Mejorados ✅

Actualizados reportes JSON/CSV para incluir:
- `detected_driver_id_path`: Qué key/método se usó para extraer `driver_id`
- `event_source_table`: Tabla fuente del evento (si hay)
- `previous_status`: Estado anterior (en modo reproceso)
- `action_taken`: Acción tomada (`quarantined`, `relinked`, `skipped`, etc.)
- `quarantine_previous_status`: Estado previo en cuarentena

### 5. Corrección de Enums ✅

Corregido manejo de enums de PostgreSQL usando `TypeDecorator`:
- `OrphanDetectedReasonEnum`: Maneja conversión automática
- `OrphanStatusEnum`: Maneja conversión automática
- Eliminados caracteres Unicode que causaban errores en Windows

## Cambios en Archivos

### Nuevos Archivos
- `backend/scripts/debug_lead_events_keys.py`: Script de diagnóstico

### Archivos Modificados
- `backend/scripts/fix_drivers_without_leads.py`:
  - Función `find_lead_events_for_driver()` completamente reescrita
  - Nueva función `extract_driver_id_from_payload()`
  - Nueva función `find_driver_id_by_license_or_phone()`
  - Nueva función `reprocess_quarantined_drivers()`
  - Argumento `--reprocess-quarantined` agregado
  - Reportes mejorados con campos adicionales

- `backend/app/models/canon.py`:
  - `OrphanDetectedReasonEnum`: TypeDecorator para manejo de enum
  - `OrphanStatusEnum`: TypeDecorator para manejo de enum
  - Corrección de columnas en `DriverOrphanQuarantine`

## Uso

### Diagnóstico
```powershell
cd backend
python scripts/debug_lead_events_keys.py
```

### Reproceso de Drivers en Cuarentena (Dry-Run)
```powershell
cd backend
python scripts/fix_drivers_without_leads.py --reprocess-quarantined --limit 100
```

### Reproceso de Drivers en Cuarentena (Ejecutar)
```powershell
cd backend
python scripts/fix_drivers_without_leads.py --reprocess-quarantined --execute --limit 100
```

### Reproceso Completo
```powershell
cd backend
python scripts/fix_drivers_without_leads.py --reprocess-quarantined --execute
```

## Pendientes / Mejoras Futuras

### 1. Validación de Resultados ⚠️
- Verificar por qué aún no encuentra eventos después de las correcciones
- Posibles causas:
  - Drivers en cuarentena no tienen `license_norm`/`phone_norm` en `drivers_index`
  - Normalización no coincide entre eventos y drivers
  - Necesidad de normalización adicional o ajustes en la comparación

### 2. Optimización de Queries ⚠️
- La búsqueda por `license/phone` trae muchos eventos (limit 100) y filtra en Python
- Considerar índice en `payload_json->>'driver_license'` y `payload_json->>'driver_phone'`
- Considerar normalización en base de datos para comparación más eficiente

### 3. Dashboard Alignment 📋
- Verificar queries del dashboard que calculan `driversWithoutLeads`
- Asegurar que usan la misma lógica de extracción
- Excluir drivers en cuarentena del conteo de "operativos"

### 4. Tests y Verificación 📋
- Agregar tests unitarios para funciones de extracción
- Agregar queries de verificación post-reproceso
- Verificar integridad: `resolved_relinked` debe tener links creados

### 5. Eventos de module_ct_cabinet_leads 📋
- Los 806 eventos de `module_ct_cabinet_leads` no tienen identificador de driver
- Investigar cómo se relacionan estos eventos con drivers
- Posible solución: buscar por `person_key` si el evento tiene uno

## Notas Técnicas

### Normalización de License/Phone
- Usa funciones `normalize_license()` y `normalize_phone()` de `app.services.normalization`
- Normalización debe ser consistente entre eventos y drivers
- Comparación se hace en Python después de normalizar ambos valores

### Restricciones Canónicas Mantenidas
- ✅ No borrar historia
- ✅ Quarantine es append-only: solo actualizar status/resolved_at/resolution_notes
- ✅ Drivers en quarantine NO se cuentan en funnel/claims/pagos
- ✅ Si hay evidencia en lead_events, puede relinkearse

## Estado Actual

- ✅ Script de diagnóstico funcional
- ✅ Función de extracción mejorada implementada
- ✅ Modo reproceso implementado
- ✅ Reportes mejorados
- ⚠️ Validación pendiente: verificar por qué no encuentra eventos
- 📋 Dashboard alignment pendiente
- 📋 Tests pendientes



