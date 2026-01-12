# Checklist de Verificación - Identity Gap & Recovery Module

Este checklist verifica que todos los componentes del módulo Identity Gap & Recovery estén funcionando correctamente.

## Fase A: Base de Datos / Migraciones

### A1: Migration aplicada
- [ ] Migration `014_create_identity_gap_recovery` aplicada sin errores
  ```bash
  cd backend
  alembic upgrade head
  ```
- [ ] Tabla `ops.identity_matching_jobs` existe
  ```sql
  SELECT COUNT(*) FROM ops.identity_matching_jobs;
  ```
- [ ] Trigger `trg_identity_origin_history` existe
  ```sql
  SELECT tgname FROM pg_trigger WHERE tgname = 'trg_identity_origin_history';
  ```

### A2: Modelos Python
- [ ] Modelo `IdentityMatchingJob` importable
  ```python
  from app.models.ops import IdentityMatchingJob
  ```
- [ ] Modelo agregado a `__init__.py`

## Fase B: Views

### B1: Vista de análisis
- [ ] Vista `ops.v_identity_gap_analysis` existe y devuelve filas
  ```sql
  SELECT COUNT(*) FROM ops.v_identity_gap_analysis;
  ```
- [ ] Vista tiene todas las columnas esperadas:
  - lead_id, lead_date, person_key, has_identity, has_origin, has_driver_activity
  - trips_14d, gap_reason, gap_age_days, risk_level
- [ ] Vista clasifica correctamente:
  ```sql
  SELECT gap_reason, COUNT(*) 
  FROM ops.v_identity_gap_analysis 
  GROUP BY gap_reason;
  ```

### B2: Vista de alertas
- [ ] Vista `ops.v_identity_gap_alerts` existe
  ```sql
  SELECT COUNT(*) FROM ops.v_identity_gap_alerts;
  ```
- [ ] Vista filtra solo alertas activas (no resolved)
- [ ] Vista tiene columnas: lead_id, alert_type, severity, days_open, suggested_action

## Fase C: Job de Matching

### C1: Job ejecutable
- [ ] Job se puede ejecutar sin errores
  ```bash
  cd backend
  python -m jobs.retry_identity_matching 10
  ```
- [ ] Job crea registros en `ops.identity_matching_jobs`
  ```sql
  SELECT COUNT(*) FROM ops.identity_matching_jobs;
  ```
- [ ] Job es idempotente (puede ejecutarse múltiples veces sin romper)

### C2: Matching funcional
- [ ] Job matchea leads con person_key existente
- [ ] Job crea `identity_link` cuando matchea
- [ ] Job crea `identity_origin` cuando matchea
- [ ] Job actualiza `attempt_count` en cada intento
- [ ] Job marca como `failed` después de MAX_ATTEMPTS

### C3: Historial
- [ ] Updates en `canon.identity_origin` crean registros en `canon.identity_origin_history`
  ```sql
  -- Hacer un update de prueba
  UPDATE canon.identity_origin 
  SET resolution_status = 'resolved_auto' 
  WHERE person_key = (SELECT person_key FROM canon.identity_origin LIMIT 1);
  
  -- Verificar que se creó registro en history
  SELECT COUNT(*) FROM canon.identity_origin_history;
  ```

## Fase D: API Endpoints

### D1: GET /api/v1/ops/identity-gaps
- [ ] Endpoint responde 200 OK
  ```bash
  curl http://localhost:8000/api/v1/ops/identity-gaps?page=1&page_size=10
  ```
- [ ] Respuesta incluye `totals`, `breakdown`, `items`, `meta`
- [ ] Filtros funcionan: `date_from`, `date_to`, `risk_level`, `gap_reason`
- [ ] Paginación funciona: `page`, `page_size`

### D2: GET /api/v1/ops/identity-gaps/alerts
- [ ] Endpoint responde 200 OK
  ```bash
  curl http://localhost:8000/api/v1/ops/identity-gaps/alerts
  ```
- [ ] Respuesta incluye `items`, `total`, `meta`
- [ ] Items tienen todas las columnas esperadas

## Fase E: UI

### E1: Sección visible
- [ ] Sección "Brechas de Identidad (Recovery)" visible en `/pagos/cobranza-yango`
- [ ] Cards muestran métricas: Total Leads, Unresolved, Resolved, High Risk
- [ ] Tabla muestra leads con brechas
- [ ] Botón "Ver Alertas" funciona

### E2: Auto-refresh
- [ ] Datos se refrescan automáticamente cada 60 segundos
- [ ] No hay errores en consola del navegador
- [ ] UI se actualiza sin recargar página completa

### E3: UX
- [ ] Colores correctos: rojo (high), amarillo (medium), gris/verde (resolved)
- [ ] Copy claro: "cada lead sin identidad puede ser plata no cobrable"
- [ ] Badges muestran gap_reason y risk_level correctamente

## Fase F: Prueba End-to-End

### F1: Flujo completo
1. [ ] Seleccionar 20 leads unresolved de la vista
   ```sql
   SELECT lead_id FROM ops.v_identity_gap_analysis 
   WHERE gap_reason != 'resolved' 
   LIMIT 20;
   ```
2. [ ] Ejecutar job
   ```bash
   python -m jobs.retry_identity_matching 20
   ```
3. [ ] Verificar que al menos algunos se resolvieron
   ```sql
   SELECT 
     COUNT(*) FILTER (WHERE status = 'matched') AS matched,
     COUNT(*) FILTER (WHERE status = 'failed') AS failed,
     COUNT(*) FILTER (WHERE status = 'pending') AS pending
   FROM ops.identity_matching_jobs;
   ```
4. [ ] Verificar que `canon.identity_origin_history` tiene registros nuevos
5. [ ] Verificar que la UI muestra los cambios

### F2: Métricas ejecutivas
- [ ] `identity_unresolved_pct` < 5% (objetivo)
- [ ] `identity_recovery_rate` > 0 (algunos se resuelven)
- [ ] `high_risk_count` se reduce con el tiempo
- [ ] `avg_days_open_unresolved` se mantiene bajo

## Comandos de Verificación Rápida

```bash
# 1. Verificar migration
cd backend
alembic current

# 2. Verificar vistas
psql -d tu_db -c "SELECT COUNT(*) FROM ops.v_identity_gap_analysis;"
psql -d tu_db -c "SELECT COUNT(*) FROM ops.v_identity_gap_alerts;"

# 3. Ejecutar job de prueba
python -m jobs.retry_identity_matching 10

# 4. Verificar API
curl http://localhost:8000/api/v1/ops/identity-gaps?page=1&page_size=5
curl http://localhost:8000/api/v1/ops/identity-gaps/alerts

# 5. Verificar UI
# Abrir http://localhost:3000/pagos/cobranza-yango
# Verificar que la sección "Brechas de Identidad" está visible
```

## Notas

- Si algún check falla, revisar logs:
  - Backend: logs de FastAPI
  - Job: output de `python -m jobs.retry_identity_matching`
  - Frontend: consola del navegador
- Para debugging, usar queries SQL directos en la base de datos
- El job es idempotente: puede ejecutarse múltiples veces sin romper
