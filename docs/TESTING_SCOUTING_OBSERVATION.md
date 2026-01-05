# Guía de Pruebas - Capa Observacional Scouting

## Paso 1: Aplicar Migraciones

### 1.1 Verificar estado de migraciones

```bash
cd backend
alembic current
```

### 1.2 Aplicar migraciones nuevas

```bash
alembic upgrade head
```

Deberías ver:
- `008_create_scouting_match_candidates` - Crea schema `observational` y tabla `scouting_match_candidates`
- `009_create_alerts_table` - Crea tabla `ops.alerts`

### 1.3 Verificar en base de datos

```sql
-- Conectar a PostgreSQL
psql -h 168.119.226.236 -U yego_user -d yego_integral

-- Verificar schema observational
\dn observational

-- Verificar tabla scouting_match_candidates
\dt observational.scouting_match_candidates

-- Verificar tabla alerts
\dt ops.alerts
```

## Paso 2: Probar Servicio de Observación (Reglas A, B, C)

### 2.1 Verificar que hay datos de scouting

```sql
-- Ver cuántos registros de scouting hay
SELECT COUNT(*) FROM public.module_ct_scouting_daily;

-- Ver rango de fechas
SELECT 
    MIN(registration_date) as fecha_min,
    MAX(registration_date) as fecha_max,
    COUNT(*) as total
FROM public.module_ct_scouting_daily;
```

### 2.2 Verificar que hay identity_links de cabinet y drivers

```sql
-- Ver links de cabinet (necesarios para Regla A y B)
SELECT COUNT(*) 
FROM canon.identity_links 
WHERE source_table = 'module_ct_cabinet_leads';

-- Ver links de drivers (necesarios para Regla C)
SELECT COUNT(*) 
FROM canon.identity_links 
WHERE source_table = 'drivers';
```

### 2.3 Ejecutar proceso observacional vía API

**Opción A: Usando curl**

```bash
# Procesar observaciones para un rango de fechas
curl -X POST "http://localhost:8000/api/v1/identity/scouting/process-observations?date_from=2025-12-01&date_to=2025-12-31" \
  -H "Content-Type: application/json"
```

**Opción B: Usando el navegador o Postman**

```
POST http://localhost:8000/api/v1/identity/scouting/process-observations?date_from=2025-12-01&date_to=2025-12-31
```

**Respuesta esperada:**
```json
{
  "message": "Observaciones procesadas exitosamente",
  "stats": {
    "processed": 150,
    "candidates_rule_a": 10,
    "candidates_rule_b": 5,
    "candidates_rule_c": 3,
    "no_candidates": 132
  }
}
```

### 2.4 Verificar resultados en base de datos

```sql
-- Ver candidatos encontrados
SELECT 
    match_rule,
    matched_source,
    COUNT(*) as cantidad,
    AVG(score) as score_promedio
FROM observational.scouting_match_candidates
GROUP BY match_rule, matched_source
ORDER BY match_rule;

-- Ver detalles de candidatos de Regla A
SELECT 
    scouting_row_id,
    scouting_date,
    week_label,
    matched_source,
    score,
    confidence_level,
    time_to_match_days,
    person_key_candidate
FROM observational.scouting_match_candidates
WHERE match_rule = 'A'
LIMIT 10;

-- Ver candidatos sin match
SELECT COUNT(*) 
FROM observational.scouting_match_candidates
WHERE matched_source = 'none';
```

### 2.5 Verificar que identity_registry NO se modificó

```sql
-- Contar registros antes
-- (Guarda este número)
SELECT COUNT(*) FROM canon.identity_registry;

-- Ejecutar proceso observacional

-- Contar registros después (debe ser igual)
SELECT COUNT(*) FROM canon.identity_registry;

-- Verificar que NO hay nuevos links de scouting
SELECT COUNT(*) 
FROM canon.identity_links 
WHERE source_table = 'module_ct_scouting_daily';
-- Debe ser 0 (scouting NO crea identity)
```

## Paso 3: Probar KPIs de Scouting

### 3.1 Obtener reporte con KPIs de scouting

**Usando curl:**

```bash
# Primero necesitas un run_id válido
# Obtener lista de runs
curl "http://localhost:8000/api/v1/ops/ingestion-runs?limit=1"

# Obtener reporte con scouting KPIs
curl "http://localhost:8000/api/v1/identity/runs/{run_id}/report?group_by=week&include_weekly=true"
```

**Usando el frontend:**

1. Ir a http://localhost:3000/runs
2. Hacer clic en "Ver Reporte" de una corrida completada
3. Cambiar a vista "Semanal (evento)"
4. Verificar que aparece la sección "Scouting — Observación (Pre-Atribución)"

### 3.2 Verificar estructura de respuesta

La respuesta debe incluir:

```json
{
  "run": {...},
  "weekly": [...],
  "weekly_trend": [...],
  "scouting_kpis": [
    {
      "week_label": "2025-W51",
      "source_table": "module_ct_scouting_daily",
      "processed_scouting": 150,
      "candidates_detected": 18,
      "candidate_rate": 12.0,
      "high_confidence_candidates": 0,
      "avg_time_to_match_days": 5.5
    }
  ]
}
```

### 3.3 Verificar cálculos manualmente

```sql
-- Verificar processed_scouting para una semana
SELECT COUNT(*) 
FROM public.module_ct_scouting_daily
WHERE to_char(date_trunc('week', registration_date::date), 'IYYY-"W"IW') = '2025-W51';

-- Verificar candidates_detected
SELECT COUNT(DISTINCT scouting_row_id)
FROM observational.scouting_match_candidates
WHERE week_label = '2025-W51'
  AND matched_source != 'none';

-- Verificar high_confidence_candidates
SELECT COUNT(*)
FROM observational.scouting_match_candidates
WHERE week_label = '2025-W51'
  AND score >= 0.80;

-- Verificar avg_time_to_match_days
SELECT AVG(time_to_match_days)
FROM observational.scouting_match_candidates
WHERE week_label = '2025-W51'
  AND time_to_match_days IS NOT NULL;
```

## Paso 4: Probar Sistema de Alertas

### 4.1 Generar datos de prueba para alertas

**Alerta 1 - Scouting sin eco:**
```sql
-- Insertar datos de prueba: scouting procesado pero sin candidatos
-- (Esto requiere que haya scouting_daily pero sin matches)
-- La alerta se genera automáticamente si processed > 50 y candidates = 0 por 2 semanas
```

**Alerta 2 - Scouting con delay alto:**
```sql
-- Insertar candidato con time_to_match_days > 14
INSERT INTO observational.scouting_match_candidates (
    week_label, scouting_row_id, scouting_date,
    person_key_candidate, matched_source, match_rule,
    score, confidence_level, matched_source_pk,
    matched_source_date, time_to_match_days
) VALUES (
    '2025-W51', 'test_delay_1', '2025-12-15',
    (SELECT person_key FROM canon.identity_registry LIMIT 1),
    'cabinet', 'A', 0.70, 'medium',
    'cabinet_test', '2025-12-30', 15
);
```

**Alerta 3 - Scouting con señal fuerte:**
```sql
-- Insertar 5+ candidatos con score >= 0.80
INSERT INTO observational.scouting_match_candidates (
    week_label, scouting_row_id, scouting_date,
    person_key_candidate, matched_source, match_rule,
    score, confidence_level, matched_source_pk,
    matched_source_date, time_to_match_days
)
SELECT 
    '2025-W51', 'test_strong_' || i, '2025-12-15',
    (SELECT person_key FROM canon.identity_registry LIMIT 1),
    'cabinet', 'A', 0.85, 'high',
    'cabinet_test_' || i, '2025-12-16', 1
FROM generate_series(1, 5) i;
```

### 4.2 Ejecutar verificación de alertas

**Opción A: Vía código Python (crear script temporal)**

```python
# test_alerts.py
from app.db import SessionLocal
from app.services.alerts import AlertService

db = SessionLocal()
try:
    service = AlertService(db)
    alerts = service.check_scouting_alerts("2025-W51", None)
    print(f"Alertas generadas: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert.alert_type}: {alert.message}")
finally:
    db.close()
```

**Opción B: Vía API (si creamos endpoint)**

```bash
# Ver alertas activas
curl "http://localhost:8000/api/v1/ops/alerts"

# Reconocer una alerta
curl -X POST "http://localhost:8000/api/v1/ops/alerts/1/acknowledge"
```

### 4.3 Verificar alertas en base de datos

```sql
-- Ver alertas activas (no reconocidas)
SELECT 
    id,
    alert_type,
    severity,
    week_label,
    message,
    created_at
FROM ops.alerts
WHERE acknowledged_at IS NULL
ORDER BY created_at DESC;

-- Ver detalles de una alerta
SELECT 
    alert_type,
    severity,
    week_label,
    message,
    details
FROM ops.alerts
WHERE id = 1;
```

### 4.4 Verificar alertas en frontend

1. Ir a http://localhost:3000
2. En el dashboard principal, deberías ver la sección "Alertas Activas"
3. Las alertas deben mostrar:
   - Badge de severity (INFO/WARNING/ERROR) con colores
   - Week label
   - Mensaje
   - Botón "Reconocer"
4. Hacer clic en "Reconocer" y verificar que la alerta desaparece

## Paso 5: Probar Tests Automatizados

### 5.1 Ejecutar tests

```bash
cd backend

# Ejecutar todos los tests de scouting
pytest tests/test_scouting_observation.py -v

# Ejecutar test específico
pytest tests/test_scouting_observation.py::test_identity_registry_not_modified -v

# Ejecutar con cobertura
pytest tests/test_scouting_observation.py --cov=app.services.scouting_observation --cov=app.services.alerts
```

### 5.2 Verificar que los tests pasan

Deberías ver:
- ✅ `test_rule_a_phone_exact_match` - Verifica Regla A
- ✅ `test_rule_b_name_similarity_city` - Verifica Regla B  
- ✅ `test_identity_registry_not_modified` - Verifica que NO se modifica identity_registry
- ✅ `test_scouting_kpis_calculation` - Verifica cálculo de KPIs
- ✅ `test_alerts_generation` - Verifica generación de alertas
- ✅ `test_high_confidence_alert` - Verifica alerta de señal fuerte

## Paso 6: Verificación End-to-End en Frontend

### 6.1 Flujo completo

1. **Dashboard Principal (http://localhost:3000)**
   - Verificar que aparecen alertas activas (si las hay)
   - Verificar colores según severity

2. **Página de Corridas (http://localhost:3000/runs)**
   - Seleccionar una corrida completada
   - Hacer clic en "Ver Reporte"
   - Cambiar a vista "Semanal (evento)"
   - Verificar que aparece la sección "Scouting — Observación (Pre-Atribución)"
   - Verificar que la tabla muestra:
     - Semana
     - Processed
     - Candidates
     - Candidate Rate
     - High Confidence
     - Avg Time to Match

3. **Filtros**
   - Seleccionar una semana específica
   - Aplicar filtros
   - Verificar que los KPIs se actualizan

## Paso 7: Verificación de Garantías

### 7.1 Verificar que scouting NO afecta KPIs de identidad

```sql
-- Antes de procesar observaciones
SELECT 
    source_table,
    COUNT(*) as total,
    SUM(CASE WHEN source_table = 'module_ct_scouting_daily' THEN 1 ELSE 0 END) as scouting_count
FROM canon.identity_links
GROUP BY source_table;

-- Procesar observaciones de scouting

-- Después (debe ser igual)
SELECT 
    source_table,
    COUNT(*) as total,
    SUM(CASE WHEN source_table = 'module_ct_scouting_daily' THEN 1 ELSE 0 END) as scouting_count
FROM canon.identity_links
GROUP BY source_table;
-- scouting_count debe seguir siendo 0
```

### 7.2 Verificar que scouting muestra 0% match en KPIs de identidad

En el frontend, en la vista semanal:
- Scouting debe aparecer con `match_rate: 0.0` o no aparecer en los KPIs de identidad
- Los KPIs de scouting están en una sección separada

## Checklist Final

- [ ] Migraciones aplicadas correctamente
- [ ] Tabla `observational.scouting_match_candidates` existe
- [ ] Tabla `ops.alerts` existe
- [ ] Endpoint `/api/v1/identity/scouting/process-observations` funciona
- [ ] Reglas A, B, C generan candidatos correctamente
- [ ] `identity_registry` NO se modifica
- [ ] KPIs de scouting se calculan correctamente
- [ ] Frontend muestra sección de scouting KPIs
- [ ] Alertas se generan correctamente
- [ ] Frontend muestra alertas activas
- [ ] Tests pasan todos
- [ ] Scouting sigue mostrando 0% match en KPIs de identidad

## Troubleshooting

### Error: "Schema observational does not exist"
```bash
# Aplicar migraciones
cd backend
alembic upgrade head
```

### Error: "No module named 'app.services.scouting_observation'"
```bash
# Verificar que el archivo existe
ls backend/app/services/scouting_observation.py

# Reiniciar el servidor backend
```

### No aparecen candidatos
- Verificar que hay datos en `module_ct_scouting_daily`
- Verificar que hay `identity_links` de cabinet o drivers
- Verificar que las fechas coinciden (ventanas de tiempo)
- Revisar logs del backend para errores

### No aparecen alertas
- Verificar que hay datos suficientes para disparar las alertas
- Verificar que las condiciones se cumplen (processed > 50, etc.)
- Ejecutar manualmente `check_scouting_alerts` desde Python


























