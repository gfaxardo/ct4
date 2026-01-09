# Discovery de Uso de Objetos DB en Repositorio

## Objetivo

Detectar automáticamente qué objetos de base de datos (tablas, vistas, materialized views) son utilizados en el código del backend, identificando si son usados por endpoints FastAPI o por scripts.

## Script

**Archivo:** `backend/scripts/discovery_usage_backend.py`

## Funcionamiento

### 1. Escaneo de Archivos

El script escanea:
- `backend/**/*.py` - Archivos Python (endpoints, servicios, scripts)
- `backend/sql/**/*.sql` - Archivos SQL

### 2. Detección de Patrones

Busca referencias a objetos DB usando patrones regex:
- `FROM schema.table`
- `JOIN schema.table`
- `schema.table` (referencias directas)
- `text("SELECT * FROM schema.table")` (queries en Python)
- `execute("SELECT * FROM schema.table")` (queries ejecutadas)

### 3. Detección de Endpoints

Identifica endpoints FastAPI buscando:
- Decoradores `@router.get("/...")`, `@router.post("/...")`, etc.
- Prefijos de router desde `include_router(..., prefix="/...")`
- Estructura de archivos en `app/api/**/*.py`

### 4. Validación contra DB

Cada objeto detectado se valida contra el catálogo de PostgreSQL para asegurar que existe:
- Consulta `pg_class` y `pg_namespace`
- Solo registra objetos con `relkind IN ('r', 'v', 'm')` (tablas, vistas, matviews)

### 5. Agrupación por Contexto

Agrupa el uso por:
- **endpoint**: Objeto usado en endpoints FastAPI
- **script**: Objeto usado en scripts o archivos SQL
- **both**: Objeto usado en ambos contextos

## Output

**Archivo CSV:** `backend/sql/ops/discovery_usage_backend.csv`

**Columnas:**
- `schema_name`: Schema del objeto
- `object_name`: Nombre del objeto
- `object_type`: Tipo (table/view/matview)
- `usage_context`: Contexto de uso (endpoint/script/both)
- `usage_locations`: JSON array con ubicaciones donde se usa
- `discovered_at`: Timestamp de descubrimiento

**Ejemplo de `usage_locations`:**
```json
[
  {
    "file": "app/api/v1/ops.py",
    "type": "endpoint",
    "endpoint_path": "/api/v1/ops/data-health"
  },
  {
    "file": "scripts/refresh_ops_mvs.py",
    "type": "script"
  }
]
```

## Uso

```bash
# Ejecutar discovery
python backend/scripts/discovery_usage_backend.py
```

**Output esperado:**
```
======================================================================
DISCOVERY DE USO DE OBJETOS DB EN REPOSITORIO
======================================================================
Inicio: 2025-01-27 10:30:00

Escaneando archivos .py y .sql...
  Objetos detectados (sin validar): 45

Validando objetos contra catálogo DB...
  Objetos válidos: 42

✓ Discovery completado. Resultados guardados en: backend/sql/ops/discovery_usage_backend.csv
  Total de objetos usados: 42

Resumen:
  Usados en endpoints: 15
  Usados en scripts: 28
  Usados en ambos: 5
```

## Limitaciones

1. **Patrones regex**: Puede tener falsos positivos si hay comentarios o strings que contengan patrones similares
2. **Validación DB**: Solo detecta objetos que existen en el momento de la ejecución
3. **Endpoints dinámicos**: Endpoints construidos dinámicamente pueden no detectarse
4. **Queries complejas**: Queries SQL muy complejas o construidas dinámicamente pueden no detectarse completamente

## Integración con Source Registry

Este script es usado por `populate_source_registry.py` para:
- Determinar `usage_context` en el registry
- Marcar objetos como `critical` si son usados por endpoints UI-ready
- Inferir `criticality` basado en el contexto de uso

## Validación

```bash
# Verificar que el CSV se generó
ls -lh backend/sql/ops/discovery_usage_backend.csv

# Ver contenido (primeras 10 líneas)
head -10 backend/sql/ops/discovery_usage_backend.csv

# Contar objetos únicos
cut -d',' -f1,2 backend/sql/ops/discovery_usage_backend.csv | sort -u | wc -l
```

## Mantenimiento

Este script debe ejecutarse:
- Después de agregar nuevos endpoints o scripts que usen objetos DB
- Antes de poblar el Source Registry
- Como parte del pipeline de CI/CD para detectar cambios en el uso

## Ejemplos de Detección

### Endpoint FastAPI
```python
# app/api/v1/ops.py
@router.get("/data-health")
def get_data_health(db: Session = Depends(get_db)):
    query = text("SELECT * FROM ops.v_identity_system_health")
    # Detecta: ops.v_identity_system_health (endpoint)
```

### Script Python
```python
# scripts/refresh_ops_mvs.py
conn.execute(text("REFRESH MATERIALIZED VIEW ops.mv_yango_payments_raw_current"))
# Detecta: ops.mv_yango_payments_raw_current (script)
```

### Archivo SQL
```sql
-- sql/ops/v_data_health.sql
SELECT * FROM public.module_ct_cabinet_leads
-- Detecta: public.module_ct_cabinet_leads (script)
```











