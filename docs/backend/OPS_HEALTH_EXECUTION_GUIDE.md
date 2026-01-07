# CT4 Ops Health — Guía de Ejecución

## Estructura del Proyecto

### Discovery Layer (Automated)

```
backend/
├── sql/ops/
│   ├── discovery_objects.sql          # Query para descubrir objetos DB
│   └── discovery_dependencies.sql     # Query para descubrir dependencias
│
└── scripts/
    ├── discovery_objects.py           # Ejecuta discovery_objects.sql → CSV
    ├── discovery_dependencies.py      # Ejecuta discovery_dependencies.sql → CSV
    └── discovery_usage_backend.py     # Escanea repo → CSV
```

**Outputs:**
- `backend/sql/ops/discovery_objects.csv`
- `backend/sql/ops/discovery_dependencies.csv`
- `backend/sql/ops/discovery_usage_backend.csv`

### Registry Layer (Canonical)

```
backend/
├── sql/ops/
│   └── source_registry.sql           # Definición de tabla
│
└── scripts/
    └── populate_source_registry.py   # Población idempotente
```

**Output:**
- Tabla `ops.source_registry` poblada

### Health Checks Layer

```
backend/sql/ops/
├── v_health_checks.sql                # Vista de checks (registry-based)
└── v_health_global.sql                # Vista de estado global
```

### API Layer

```
backend/app/
├── api/v1/
│   └── ops.py                         # Endpoints de health
└── schemas/
    ├── ops_source_registry.py         # Schemas para registry
    ├── ops_health_checks.py           # Schemas para checks
    └── ops_health_global.py           # Schemas para global
```

### UI Layer

```
frontend/
├── app/ops/health/
│   └── page.tsx                       # Página principal con tabs
└── components/ops/
    ├── IdentitySystemHealthPanel.tsx  # Tab Identity
    ├── RawDataHealthPanel.tsx          # Tab RAW
    ├── MvHealthPanel.tsx              # Tab MV
    └── HealthChecksPanel.tsx          # Tab Checks
```

---

## Orden de Ejecución

### Fase 1: Setup Inicial (Una vez)

```bash
# 1. Crear tabla registry
psql -h <host> -p <port> -U <user> -d <database> \
  -f backend/sql/ops/source_registry.sql

# 2. Crear/actualizar vistas de health
psql -h <host> -p <port> -U <user> -d <database> \
  -f backend/sql/ops/v_health_checks.sql

psql -h <host> -p <port> -U <user> -d <database> \
  -f backend/sql/ops/v_health_global.sql
```

### Fase 2: Discovery (Ejecutar en orden)

```bash
cd backend

# 2.1 Descubrir objetos DB
python scripts/discovery_objects.py
# → Genera: sql/ops/discovery_objects.csv

# 2.2 Descubrir dependencias
python scripts/discovery_dependencies.py
# → Genera: sql/ops/discovery_dependencies.csv

# 2.3 Descubrir uso en repo
python scripts/discovery_usage_backend.py
# → Genera: sql/ops/discovery_usage_backend.csv
```

**Nota:** Si algún script falla, puede continuarse con los demás (tolerancia a errores parciales). El registry fallará si no puede conectar a DB.

### Fase 3: Población del Registry

```bash
# 3. Poblar registry (idempotente, puede ejecutarse múltiples veces)
python scripts/populate_source_registry.py
# → Lee: discovery_objects.csv, discovery_dependencies.csv, discovery_usage_backend.csv
# → Actualiza: ops.source_registry
```

**Nota:** Este script es idempotente. Respeta overrides manuales.

### Fase 4: Health Checks (Automático)

Los health checks se evalúan automáticamente al consultar `ops.v_health_checks` (es una vista).

```bash
# Verificar checks
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT check_key, severity, status FROM ops.v_health_checks ORDER BY severity, check_key;"
```

### Fase 5: Validación

```bash
# 5.1 Verificar registry
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT count(*) FROM ops.source_registry;"
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT schema_name, object_name, criticality, layer FROM ops.source_registry WHERE criticality = 'critical' LIMIT 10;"

# 5.2 Verificar health global
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT * FROM ops.v_health_global;"

# 5.3 Probar endpoints
curl "http://localhost:8000/api/v1/ops/source-registry?limit=10&offset=0"
curl "http://localhost:8000/api/v1/ops/health-checks"
curl "http://localhost:8000/api/v1/ops/health-global"
curl "http://localhost:8000/api/v1/ops/mv-health?limit=5"

# 5.4 Verificar UI
# Abrir: http://localhost:3000/ops/health?tab=mv
```

---

## Preguntas Abiertas - Respuestas Implementadas

### 1. Frecuencia de Discovery

**Pregunta:** ¿Con qué frecuencia ejecutar discovery?

**Respuesta Implementada:**
- **Default:** Diario (recomendado para producción)
- **Desarrollo:** On-demand
- **CI/CD:** Opcional hook en cambios de código

**Implementación:**
- Scripts son idempotentes, pueden ejecutarse en cualquier momento
- No hay bloqueo de ejecución frecuente
- Recomendación: cron diario a las 2 AM

### 2. Propagación de Criticidad

**Pregunta:** ¿Debe propagarse criticidad por cadena de dependencias?

**Respuesta Implementada:**
- **Default:** Sí, implementado
- **Lógica:** RAW que alimenta MV crítica → `critical`
- **Método:** Función `propagate_criticality()` en `populate_source_registry.py`

**Implementación:**
```python
# Si MV es critical, sus parents RAW se vuelven critical
for mv_key in critical_mvs:
    parents = dependencies.get(mv_key, [])
    for parent in parents:
        if parent_data.get("layer") == "RAW":
            parent_data["criticality"] = "critical"
```

### 3. Manejo de Errores Parciales

**Pregunta:** ¿Qué hacer si discovery falla parcialmente?

**Respuesta Implementada:**
- **Discovery:** Tolerante a errores parciales
  - Si un CSV no se genera, se muestra warning pero continúa
  - Scripts individuales pueden fallar sin afectar otros
- **Registry:** Falla si DB no responde
  - No puede hacer UPSERT sin conexión a DB
  - Error explícito con traceback completo

**Implementación:**
- Discovery scripts: `try/except` con warnings
- Registry script: `try/except` con rollback y error explícito

### 4. Objetos Usados por Endpoints

**Pregunta:** ¿Qué criticality para objetos usados por endpoints?

**Respuesta Implementada:**
- **Default:** `critical` (no `important`)
- **Razón:** Objetos expuestos vía API son críticos para operación

**Implementación:**
```python
# Usado por endpoint => critical
if usage_context and "endpoint" in usage_context:
    return "critical"
```

### 5. MV Refresh Schedule Auto-detección

**Pregunta:** ¿Auto-detectar refresh_schedule desde logs?

**Respuesta Implementada:**
- **Default:** Manual por ahora (campo `refresh_schedule` en registry)
- **Futuro:** Auto-detectar desde `ops.mv_refresh_log` (fase 2)

**Implementación Actual:**
- Campo `refresh_schedule` existe pero se deja NULL
- Puede poblarse manualmente o en fase 2 con análisis de logs

### 6. Unregistered Used Object Detection

**Pregunta:** ¿Cómo detectar objetos usados pero no registrados?

**Respuesta Implementada:**
- **Método Actual:** Aproximación (objetos en DB pero no en registry)
- **Mejora Futura:** Cross-reference directo con `discovery_usage_backend.csv`

**Implementación:**
- Check `unregistered_used_object` detecta objetos en schemas críticos no en registry
- Limitado a `ops`, `canon`, y `public.module_ct_%`
- Mejora: agregar tabla temporal o query directa al CSV

---

## Checklist de Validación

### Pre-requisitos
- [ ] PostgreSQL accesible
- [ ] Python 3.8+ con dependencias instaladas
- [ ] Backend configurado con `DATABASE_URL`
- [ ] Frontend configurado con `NEXT_PUBLIC_API_BASE_URL`

### Discovery
- [ ] `discovery_objects.csv` generado con objetos
- [ ] `discovery_dependencies.csv` generado con dependencias
- [ ] `discovery_usage_backend.csv` generado con uso

### Registry
- [ ] Tabla `ops.source_registry` creada
- [ ] Registry poblado con objetos descubiertos
- [ ] Overrides manuales respetados
- [ ] Criticidad propagada correctamente

### Health Checks
- [ ] Vista `ops.v_health_checks` creada
- [ ] Todos los checks presentes (8 checks)
- [ ] Checks derivan de registry (no hardcode)
- [ ] `drilldown_url` correctos

### API
- [ ] Endpoint `/api/v1/ops/source-registry` funciona
- [ ] Endpoint `/api/v1/ops/health-checks` funciona
- [ ] Endpoint `/api/v1/ops/health-global` funciona
- [ ] Endpoint `/api/v1/ops/mv-health` funciona
- [ ] Errores retornan `detail="database_error"`

### UI
- [ ] Página `/ops/health` carga
- [ ] Badge global muestra estado correcto
- [ ] Tab Identity funciona
- [ ] Tab RAW funciona
- [ ] Tab MV funciona (no PENDING)
- [ ] Tab Checks funciona con drilldowns

---

## Comandos Rápidos

### Ejecución Completa

```bash
# Setup inicial (una vez)
psql -f backend/sql/ops/source_registry.sql
psql -f backend/sql/ops/v_health_checks.sql
psql -f backend/sql/ops/v_health_global.sql

# Discovery + Registry (regular)
cd backend
python scripts/discovery_objects.py && \
python scripts/discovery_dependencies.py && \
python scripts/discovery_usage_backend.py && \
python scripts/populate_source_registry.py
```

### Verificación Rápida

```bash
# Registry
psql -c "SELECT count(*), count(*) FILTER (WHERE criticality = 'critical') FROM ops.source_registry;"

# Health
psql -c "SELECT global_status, error_count, warn_count FROM ops.v_health_global;"

# API
curl -s "http://localhost:8000/api/v1/ops/health-global" | jq .
```

---

## Troubleshooting

### Discovery no encuentra objetos

**Síntoma:** CSVs vacíos o con pocos objetos

**Solución:**
- Verificar que schemas existan: `SELECT nspname FROM pg_namespace WHERE nspname IN ('public', 'ops', 'canon', 'raw', 'observational');`
- Verificar permisos de lectura en `pg_class`
- Verificar que objetos no estén filtrados por `pg_%`

### Registry no se puebla

**Síntoma:** `populate_source_registry.py` no inserta registros

**Solución:**
- Verificar que CSVs existan y tengan datos
- Verificar conexión a DB (`DATABASE_URL`)
- Verificar permisos de escritura en schema `ops`
- Revisar logs del script para errores específicos

### Health checks siempre OK

**Síntoma:** Todos los checks muestran status=OK

**Solución:**
- Verificar que registry tenga datos: `SELECT count(*) FROM ops.source_registry;`
- Verificar que registry tenga objetos con `should_monitor=true`
- Verificar que vistas de health existan: `SELECT * FROM ops.v_data_health_status LIMIT 1;`

### UI no muestra datos

**Síntoma:** Tabs vacíos o errores en frontend

**Solución:**
- Verificar que backend esté corriendo: `curl http://localhost:8000/health`
- Verificar que endpoints retornen datos: `curl http://localhost:8000/api/v1/ops/health-checks`
- Verificar CORS si frontend y backend en diferentes puertos
- Revisar console del navegador para errores JavaScript

---

## Mantenimiento

### Agregar Nuevo Check

1. Agregar check a `backend/sql/ops/v_health_checks.sql`
2. Debe derivar de `ops.source_registry` (no hardcode)
3. Agregar `drilldown_url` en el CASE
4. Ejecutar: `psql -f backend/sql/ops/v_health_checks.sql`

### Modificar Heurísticas

1. Editar funciones en `backend/scripts/populate_source_registry.py`:
   - `infer_layer()`
   - `infer_role()`
   - `infer_criticality()`
   - `propagate_criticality()`
2. Re-ejecutar: `python scripts/populate_source_registry.py`

### Agregar Override Manual

```sql
UPDATE ops.source_registry
SET is_critical = true,
    notes = 'Marcado manualmente como crítico'
WHERE schema_name = 'ops' AND object_name = 'v_important_view';
```

El script `populate_source_registry.py` NO pisará estos valores.

---

## Referencias

- [Arquitectura del Sistema](OPS_HEALTH_SYSTEM_ARCHITECTURE.md)
- [Discovery Usage Backend](discovery_usage_backend.md)
- [Source Registry](source_registry.md)









