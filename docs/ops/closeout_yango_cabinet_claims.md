# Closeout: Yango Cabinet Claims - Checklist Final

## ¿Qué es "Done"?

- ✅ Endpoints B1/B2/B3 funcionando (claims-to-collect, drilldown, export CSV)
- ✅ Frontend `/pagos/yango-cabinet-claims` accesible desde sidebar
- ✅ MV `ops.mv_yango_cabinet_claims_for_collection` refrescando correctamente
- ✅ Health check `ops.v_yango_cabinet_claims_mv_health` disponible
- ✅ Índice único creado (permite REFRESH CONCURRENTLY)
- ✅ Script `deploy_verify_yango_cabinet_claims.ps1` pasa todos los checks

---

## Orden de Ejecución en Deploy Nuevo

### Paso 1: Aplicar migración mv_refresh_log_extended

```bash
cd backend
python scripts/apply_mv_refresh_log_extended.py
```

**Verificar:** Debe mostrar "✓ Verificación: todas las columnas nuevas existen"

---

### Paso 2: Aplicar view health SQL

```bash
psql "$DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_health.sql
```

**Verificar:**
```sql
SELECT * FROM ops.v_yango_cabinet_claims_mv_health;
```

Debe retornar 1 fila con `status_bucket` (OK/WARN/CRIT/NO_REFRESH).

---

### Paso 3: Verificar duplicados MV

```bash
psql "$DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_duplicates.sql
```

**Verificar Query 2:** Debe retornar 0 filas (sin duplicados).

Si hay duplicados → resolver antes de continuar.

---

### Paso 4: Crear índice único (si no hay duplicados)

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql
```

**Verificar:**
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'ops' 
  AND tablename = 'mv_yango_cabinet_claims_for_collection'
  AND indexname = 'ux_mv_yango_cabinet_claims_for_collection_grain';
```

Debe retornar 1 fila.

---

### Paso 5: Correr refresh manual

```bash
cd backend
python scripts/refresh_yango_cabinet_claims_mv.py
```

**Verificar:** Debe mostrar "[OK] Refresh completado exitosamente" y status=OK en log.

---

### Paso 6: Correr deploy_verify gate

```bash
.\docs\ops\deploy_verify_yango_cabinet_claims.ps1
```

**Verificar:** Todos los checks deben pasar (o warnings aceptables).

---

## Verificación en UI

### 1. Ruta `/pagos/yango-cabinet-claims`

- Abrir navegador: `http://localhost:3000/pagos/yango-cabinet-claims`
- Acceso: Sidebar → Pagos → Yango → Claims Cabinet
- Verificar: Tabla carga con datos (o mensaje "No hay claims")

### 2. Export CSV

- Click botón "Exportar CSV"
- Verificar: Descarga archivo CSV con nombre `yango_cabinet_claims_YYYYMMDD_HHMM.csv`
- Abrir en Excel: Debe abrir correctamente (UTF-8 BOM)

### 3. Drilldown

- Click en una fila de la tabla
- Verificar: Modal se abre mostrando:
  - Información del claim
  - Lead cabinet
  - Payment exact (si existe)
  - Payments other milestones (si existen)
  - Reconciliation
  - Misapplied explanation (si aplica)

### 4. Endpoint `/mv-health`

```bash
curl http://localhost:8000/api/v1/yango/cabinet/mv-health
```

**Verificar:**
- Status 200
- `status_bucket` ∈ {"OK", "WARN", "CRIT", "NO_REFRESH"}
- `hours_since_ok_refresh` < 24 (idealmente)

---

## Comandos Rápidos de Verificación

### Health check SQL
```sql
SELECT * FROM ops.v_yango_cabinet_claims_mv_health;
```

### Último refresh
```sql
SELECT status, rows_after_refresh, refresh_finished_at
FROM ops.mv_refresh_log
WHERE schema_name = 'ops' 
  AND mv_name = 'mv_yango_cabinet_claims_for_collection'
ORDER BY refresh_started_at DESC
LIMIT 1;
```

### Endpoints (curl)
```bash
# B1: Claims to collect
curl "http://localhost:8000/api/v1/yango/cabinet/claims-to-collect?limit=10"

# B2: Drilldown (requiere driver_id real)
curl "http://localhost:8000/api/v1/yango/cabinet/claims/DRIVER_ID/1/drilldown"

# B3: Export CSV
curl "http://localhost:8000/api/v1/yango/cabinet/claims/export" -o test_export.csv

# MV Health
curl "http://localhost:8000/api/v1/yango/cabinet/mv-health"
```

---

## Troubleshooting Rápido

### MV no refresca
```bash
cd backend
python scripts/refresh_yango_cabinet_claims_mv.py
```

### Health check muestra CRIT
- Verificar último refresh: `SELECT * FROM ops.mv_refresh_log ...`
- Si status=ERROR: revisar `error_message`
- Reintentar refresh manual

### Endpoint 404
- Verificar que backend está corriendo
- Verificar que MV existe: `SELECT * FROM pg_matviews WHERE matviewname = 'mv_yango_cabinet_claims_for_collection'`

### Frontend no carga
- Verificar que frontend está corriendo en `http://localhost:3000`
- Verificar consola del navegador para errores
- Verificar que endpoint B1 responde correctamente

---

## Referencias

- Runbook refresh: `docs/runbooks/scheduler_refresh_mvs.md`
- SQL duplicados: `docs/ops/yango_cabinet_claims_mv_duplicates.sql`
- SQL índice único: `backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql`
- Script deploy verify: `docs/ops/deploy_verify_yango_cabinet_claims.ps1`
- Script refresh: `backend/scripts/refresh_yango_cabinet_claims_mv.py`

