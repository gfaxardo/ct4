# Instrucciones de Deploy: Sistema de Eliminación de Drivers Huérfanos (Orphans)

## 📋 Resumen

Este documento describe el proceso de deploy del sistema de eliminación definitiva de drivers huérfanos (orphans) del sistema CT4 Identity.

**Objetivo Canónico**: Eliminar definitivamente el concepto de "drivers fantasma" sin perder historia ni auditabilidad.

**Regla de Oro**: Un driver NO puede existir operativamente si no proviene de un lead válido.

---

## ⚠️ Pre-requisitos

1. ✅ Base de datos PostgreSQL accesible
2. ✅ Alembic configurado y funcionando
3. ✅ Python 3.9+ con dependencias instaladas
4. ✅ Backup completo de la base de datos antes de deploy
5. ✅ Acceso a ejecutar migraciones y scripts
6. ✅ Acceso a la base de datos para verificaciones post-deploy

---

## 📦 Componentes a Deployar

### A) Backend / Data Layer

1. **Migración Alembic**: `canon.driver_orphan_quarantine` (tabla append-only)
2. **Modelos SQLAlchemy**: `DriverOrphanQuarantine` con enums
3. **Vistas SQL actualizadas**:
   - `ops.v_cabinet_funnel_status` (excluye orphans)
   - `ops.v_payment_calculation` (excluye orphans)
   - `ops.v_ct4_eligible_drivers` (excluye orphans)
   - `ops.v_driver_orphans` (nueva vista de auditoría)
4. **Script de limpieza**: `backend/scripts/fix_drivers_without_leads.py`
5. **Endpoints API**: `/api/v1/identity/orphans/*`

### B) Frontend / UI Layer

1. **Página Orphans**: `/orphans`
2. **Dashboard actualizado**: Card de métricas de orphans
3. **Tipos TypeScript**: Interfaces para Orphans
4. **Funciones API**: `getOrphans`, `getOrphansMetrics`, `runOrphansFix`

### C) Tests / Verificación

1. **Tests de integridad**: `backend/tests/test_orphans_integrity.py`
2. **SQL de verificación**: `backend/sql/ops/verify_no_orphans_outside_quarantine.sql`

---

## 🚀 Proceso de Deploy (Paso a Paso)

### FASE 1: Preparación y Backup

```bash
# 1. Backup completo de la base de datos
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f backup_pre_orphans_$(date +%Y%m%d_%H%M%S).dump

# 2. Verificar conectividad
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT version();"

# 3. Verificar estado actual de drivers sin leads
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f backend/sql/ops/verify_no_orphans_outside_quarantine.sql
```

**Salida esperada**: Lista de drivers sin leads actuales (si existen).

---

### FASE 2: Deploy de Migración Alembic

```bash
# 1. Navegar al directorio backend
cd backend

# 2. Verificar migración pendiente
alembic current
alembic heads
alembic history

# 3. Aplicar migración (CREAR tabla canon.driver_orphan_quarantine)
alembic upgrade head

# 4. Verificar que la tabla se creó correctamente
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    SELECT table_name, table_schema 
    FROM information_schema.tables 
    WHERE table_schema = 'canon' 
    AND table_name = 'driver_orphan_quarantine';
"
```

**Salida esperada**: 
```
 table_name              | table_schema 
-------------------------+--------------
 driver_orphan_quarantine | canon
(1 row)
```

---

### FASE 3: Deploy de Modelos SQLAlchemy

```bash
# 1. Verificar que los modelos estén importados correctamente
python -c "
from app.models.canon import DriverOrphanQuarantine, OrphanDetectedReason, OrphanStatus
print('✅ Modelos importados correctamente')
print(f'   - DriverOrphanQuarantine: {DriverOrphanQuarantine}')
print(f'   - OrphanDetectedReason: {OrphanDetectedReason}')
print(f'   - OrphanStatus: {OrphanStatus}')
"

# 2. Verificar estructura de la tabla
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    \d canon.driver_orphan_quarantine
"
```

**Salida esperada**: Descripción completa de la tabla con todos los campos.

---

### FASE 4: Deploy de Vistas SQL Actualizadas

```bash
# 1. Aplicar vistas actualizadas (en orden de dependencias)

# 4.1. Vista de auditoría (nueva)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f backend/sql/ops/v_driver_orphans.sql

# 4.2. Vista de funnel (actualizada)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f backend/sql/ops/v_cabinet_funnel_status.sql

# 4.3. Vista de cálculo de pagos (actualizada)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f backend/sql/ops/v_payment_calculation.sql

# 4.4. Vista de drivers elegibles (actualizada)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f backend/sql/ops/v_ct4_eligible_drivers.sql

# 2. Verificar que las vistas se crearon/actualizaron correctamente
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    SELECT table_name 
    FROM information_schema.views 
    WHERE table_schema = 'ops' 
    AND table_name IN (
        'v_driver_orphans',
        'v_cabinet_funnel_status',
        'v_payment_calculation',
        'v_ct4_eligible_drivers'
    )
    ORDER BY table_name;
"
```

**Salida esperada**: 4 filas con las vistas listadas.

---

### FASE 5: Verificación de Exclusión de Orphans en Vistas

```bash
# Verificar que las vistas excluyen drivers en cuarentena
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    -- Verificar que v_cabinet_funnel_status excluye orphans
    SELECT COUNT(*) as drivers_in_funnel
    FROM ops.v_cabinet_funnel_status
    WHERE driver_id IN (
        SELECT driver_id 
        FROM canon.driver_orphan_quarantine 
        WHERE status = 'quarantined'
    );
"
```

**Salida esperada**: `0` (ningún driver en cuarentena debe aparecer en funnel).

---

### FASE 6: Deploy de Backend (API Endpoints)

```bash
# 1. Verificar que el servidor backend esté corriendo o reiniciarlo
cd backend

# 2. Verificar endpoints disponibles
curl http://localhost:8000/api/v1/identity/orphans/metrics

# 3. Si hay errores, verificar logs
tail -f logs/app.log
```

**Salida esperada**: Respuesta JSON con métricas de orphans (puede estar vacío si no hay orphans aún).

---

### FASE 7: Ejecución de Script de Limpieza (DRY-RUN primero)

```bash
# 1. EJECUTAR DRY-RUN primero (NO aplica cambios)
cd backend
python scripts/fix_drivers_without_leads.py --limit 100

# 2. Revisar reportes generados en ./output/
ls -lh output/orphans_report_*.json
ls -lh output/orphans_report_*.csv

# 3. Revisar reporte JSON
cat output/orphans_report_*.json | jq '.stats'

# 4. Revisar muestra de drivers (primeros 10)
cat output/orphans_report_*.json | jq '.drivers[:10]'
```

**Salida esperada**: 
- Reporte JSON con `stats` mostrando totales
- Reporte CSV con lista de drivers
- Muestra de drivers en consola

---

### FASE 8: Ejecución Real (Solo después de revisar DRY-RUN)

```bash
# ⚠️ ATENCIÓN: Solo ejecutar después de revisar DRY-RUN
# ⚠️ Este comando APLICA CAMBIOS REALES en la base de datos

cd backend
python scripts/fix_drivers_without_leads.py --execute --limit 100

# 2. Revisar resultados
cat output/orphans_report_*.json | jq '.stats'
```

**Salida esperada**: 
- `resolved_relinked`: drivers reparados con links creados
- `quarantined`: drivers enviados a cuarentena
- `errors`: 0 (si todo salió bien)

---

### FASE 9: Deploy de Frontend

```bash
# 1. Navegar al directorio frontend
cd frontend

# 2. Instalar dependencias (si es necesario)
npm install

# 3. Build del frontend (si es necesario)
npm run build

# 4. Verificar que las páginas existan
ls -la app/orphans/page.tsx
ls -la components/Sidebar.tsx

# 5. Si hay servidor de desarrollo, reiniciarlo
npm run dev
```

---

### FASE 10: Verificación Post-Deploy (CRÍTICO)

Ejecutar queries de verificación completas:

```bash
# Ejecutar todos los tests de verificación
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f backend/sql/ops/verify_no_orphans_outside_quarantine.sql

# Ejecutar tests de integridad (Python)
cd backend
pytest tests/test_orphans_integrity.py -v
```

**Salida esperada**: Todos los tests deben pasar (ver sección de Criterios de Aceptación).

---

## ✅ Criterios de Aceptación (Post-Deploy)

### 1. Integridad de Datos

```sql
-- ✅ Drivers sin lead operativos = 0
SELECT COUNT(*) as violation_count
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
-- Debe retornar: 0
```

### 2. Exclusión Operativa

```sql
-- ✅ Funnel excluye orphans
SELECT COUNT(*) as orphans_in_funnel
FROM ops.v_cabinet_funnel_status vfs
WHERE vfs.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
-- Debe retornar: 0

-- ✅ Pagos excluyen orphans
SELECT COUNT(*) as orphans_in_payments
FROM ops.v_payment_calculation vpc
WHERE vpc.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
-- Debe retornar: 0

-- ✅ Elegibilidad excluye orphans
SELECT COUNT(*) as orphans_in_eligible
FROM ops.v_ct4_eligible_drivers ved
WHERE ved.driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
-- Debe retornar: 0
```

### 3. Auditoría Completa

```sql
-- ✅ Todo driver sin lead tiene registro en quarantine
SELECT COUNT(*) as missing_quarantine_records
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id FROM canon.driver_orphan_quarantine
);
-- Debe retornar: 0
```

### 4. UI Funcional

- ✅ Dashboard muestra card de métricas de orphans
- ✅ Página `/orphans` carga y muestra lista de orphans
- ✅ Botones de ejecutar fix funcionan (dry-run y execute)
- ✅ Filtros funcionan correctamente

### 5. Prevención Futura

- ✅ Tests de integridad pasan
- ✅ `IngestionService._link_driver()` verifica leads antes de crear links
- ✅ `LeadAttributionService.ensure_driver_identity_link()` ya protegido

---

## 🔄 Rollback (Si es Necesario)

Si algo sale mal durante el deploy:

```bash
# 1. Restaurar backup de base de datos
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -c backup_pre_orphans_*.dump

# 2. Revertir migración Alembic
cd backend
alembic downgrade -1

# 3. Revertir vistas SQL (a versiones anteriores sin exclusión de orphans)
# (Requiere mantener versiones anteriores de las vistas)
```

---

## 📝 Notas Importantes

1. **Append-Only**: La tabla `canon.driver_orphan_quarantine` es append-only. Nunca borrar filas.

2. **Dry-Run Primero**: Siempre ejecutar `--dry-run` antes de `--execute` para revisar cambios.

3. **Límites Incrementales**: Usar `--limit` para procesar en lotes pequeños inicialmente.

4. **Monitoreo Continuo**: Ejecutar queries de verificación periódicamente para detectar nuevos orphans.

5. **Prevención**: El código de matching/ingestion ya está protegido para evitar crear nuevos orphans.

---

## 🆘 Troubleshooting

### Error: "Table already exists"
```bash
# Verificar si la tabla existe
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d canon.driver_orphan_quarantine"

# Si existe, verificar estructura. Si no coincide, puede necesitar recrearse.
```

### Error: "View already exists"
```bash
# Las vistas se recrean con CREATE OR REPLACE, debería funcionar.
# Si hay errores, verificar dependencias:
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d+ ops.v_cabinet_funnel_status"
```

### Error: "Foreign key constraint"
```bash
# Verificar que no hay referencias activas a drivers que se están poniendo en cuarentena
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    SELECT COUNT(*) 
    FROM ops.v_cabinet_funnel_status 
    WHERE driver_id IN (SELECT driver_id FROM canon.driver_orphan_quarantine WHERE status = 'quarantined');
"
```

---

## 📞 Contacto y Soporte

Para problemas durante el deploy:
1. Revisar logs: `backend/logs/app.log`
2. Revisar reportes: `backend/output/orphans_report_*.json`
3. Ejecutar queries de verificación: `backend/sql/ops/verify_no_orphans_outside_quarantine.sql`

---

**Última actualización**: $(date +%Y-%m-%d)
**Versión**: 1.0.0



