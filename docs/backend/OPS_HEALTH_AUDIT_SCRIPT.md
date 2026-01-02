# CT4 Ops Health — Script de Auditoría Automática

## Objetivo

El script `run_ops_health_audit.py` ejecuta automáticamente todo el flujo de discovery, registry y validaciones, generando reportes que permiten responder:

- ¿Estamos cubriendo todas las fuentes reales?
- ¿Hay fuentes usadas que no están registradas?
- ¿Hay fuentes críticas sin monitoreo?
- ¿Hay RAW stale afectando componentes críticos?
- ¿El sistema puede declararse HEALTHY o NO?

## Uso

```bash
# Desde el directorio raíz del proyecto
python backend/scripts/run_ops_health_audit.py
```

## Flujo de Ejecución

### Fase 1: Discovery
1. Ejecuta `discovery_objects.py` → `discovery_objects.csv`
2. Ejecuta `discovery_dependencies.py` → `discovery_dependencies.csv`
3. Ejecuta `discovery_usage_backend.py` → `discovery_usage_backend.csv`

**Si algún script falla:** El proceso aborta con exit code 2.

### Fase 2: Source Registry
1. Ejecuta `populate_source_registry.py`
2. Respeta overrides manuales (NO pisa columnas manuales)
3. Registra timestamp de ejecución

**Si falla:** El proceso aborta con exit code 2.

### Fase 3: Validaciones Automáticas

Ejecuta queries SQL que evalúan:

#### A. Coverage Real
- Total objetos descubiertos (desde CSV)
- Total objetos en registry
- Objetos en DB pero no registrados
- Objetos registrados pero no existentes

#### B. Uso Sin Registro
- Objetos usados en código pero no en registry
- Objetos monitoreados pero no cubiertos por health views

#### C. Fuentes Esperadas Faltantes
- Objetos marcados como `is_expected=true` pero no existen en DB

#### D. Impacto Real
- RAW stale que afecta MVs críticas
- MVs con refresh fallido
- MVs no pobladas
- MVs críticas sin historial de refresh

#### E. Estado Global
- Lee `ops.v_health_global` para estado agregado

### Fase 4: Clasificación Automática

**Reglas:**
- ❌ **CRITICAL**: Cualquier check con `severity=error` y `status=ERROR`
- ⚠️ **WARNING**: Warnings sin errores críticos
- ✅ **OK**: Ningún error ni warning

**Exit Codes:**
- `0`: OK
- `1`: WARNING
- `2`: CRITICAL

### Fase 5: Generación de Reportes

Genera 2 archivos automáticamente:

#### A. Markdown (Humano)
`docs/backend/OPS_HEALTH_AUDIT_REPORT.md`

Contiene:
- Timestamp de ejecución
- Resumen ejecutivo (OK/WARN/ERROR)
- Tabla de checks fallidos
- Listado de objetos no registrados
- Listado de objetos usados sin registro
- Impactos críticos detallados
- Recomendaciones automáticas

#### B. JSON (Máquina)
`docs/backend/OPS_HEALTH_AUDIT_REPORT.json`

Estructura:
```json
{
  "timestamp": "2025-01-27T10:30:00",
  "summary": {
    "status": "OK|WARNING|CRITICAL",
    "global_status": "OK|WARN|ERROR",
    "error_count": 0,
    "warn_count": 0,
    "ok_count": 13
  },
  "coverage": {
    "discovered_objects": 45,
    "registered_objects": 42,
    "unregistered_count": 3,
    "missing_count": 0
  },
  "checks": [...],
  "uncovered_objects": [...],
  "unregistered_used_objects": [...],
  "critical_impacts": {
    "raw_stale_affecting_critical": [...],
    "mv_refresh_failed": [...],
    "mv_not_populated": [...],
    "critical_mv_no_refresh_log": [...]
  }
}
```

## Ejemplo de Salida

```
======================================================================
CT4 OPS HEALTH — AUDITORÍA AUTOMÁTICA
======================================================================
Inicio: 2025-01-27 10:30:00

======================================================================
FASE 1: DISCOVERY
======================================================================
  Ejecutando discovery_objects.py...
✓ discovery_objects.py completado
    ✓ Discovery completado. Resultados guardados en: ...
    Total de objetos encontrados: 45

  Ejecutando discovery_dependencies.py...
✓ discovery_dependencies.py completado
    ✓ Discovery de dependencias completado. Resultados guardados en: ...
    Total de dependencias encontradas: 23

  Ejecutando discovery_usage_backend.py...
✓ discovery_usage_backend.py completado
    ✓ Discovery completado. Resultados guardados en: ...
    Total de objetos usados: 38

======================================================================
FASE 2: SOURCE REGISTRY
======================================================================
  Ejecutando populate_source_registry.py...
✓ Registry poblado exitosamente
    Nuevos registros: 42
    Registros actualizados: 0
    Total procesados: 42

======================================================================
FASE 3: VALIDACIONES
======================================================================
### A. Coverage Real
  Objetos en DB no registrados...
✓ Objetos en DB no registrados: 3
  Objetos registrados pero no existentes...
✓ Objetos registrados pero no existentes: 0

### B. Health Checks
  Obteniendo health checks...
✓ Obteniendo health checks: 13

### C. Estado Global
  Obteniendo estado global...
✓ Obteniendo estado global: 1

### D. Objetos Usados Sin Registro
  Obteniendo objetos usados sin registro...
✓ Objetos usados sin registro: 2

### E. Impactos Críticos
  RAW stale afectando MVs críticas...
✓ RAW stale afectando MVs críticas: 0
  MVs con refresh fallido...
✓ MVs con refresh fallido: 0
  MVs no pobladas...
✓ MVs no pobladas: 0
  MVs críticas sin refresh log...
✓ MVs críticas sin refresh log: 1

======================================================================
FASE 4: GENERACIÓN DE REPORTES
======================================================================
✓ Reporte Markdown generado: docs/backend/OPS_HEALTH_AUDIT_REPORT.md
✓ Reporte JSON generado: docs/backend/OPS_HEALTH_AUDIT_REPORT.json

======================================================================
RESUMEN FINAL
======================================================================
Estado: WARNING

  Errores: 0
  Advertencias: 2
  OK: 11

  Objetos descubiertos: 45
  Objetos registrados: 42
  Objetos no registrados: 3
  Objetos usados sin registro: 2

⚠️  SISTEMA CON ADVERTENCIAS
   Revisar reportes para recomendaciones.

Reportes disponibles en:
  - docs/backend/OPS_HEALTH_AUDIT_REPORT.md
  - docs/backend/OPS_HEALTH_AUDIT_REPORT.json
```

## Integración con CI/CD

### Ejecución en Pipeline

```yaml
# Ejemplo GitHub Actions
- name: Run Ops Health Audit
  run: |
    python backend/scripts/run_ops_health_audit.py
  continue-on-error: true

- name: Upload Audit Reports
  uses: actions/upload-artifact@v3
  with:
    name: ops-health-audit
    path: docs/backend/OPS_HEALTH_AUDIT_REPORT.*
```

### Cron Job (Producción)

```bash
# Ejecutar diariamente a las 2 AM
0 2 * * * cd /path/to/CT4 && python backend/scripts/run_ops_health_audit.py >> /var/log/ops-health-audit.log 2>&1
```

### Alertas Automáticas

```bash
# Script wrapper para alertas
#!/bin/bash
python backend/scripts/run_ops_health_audit.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    # CRITICAL: Enviar alerta inmediata
    send_alert "CRITICAL: Ops Health audit detectó errores críticos"
    exit 2
elif [ $EXIT_CODE -eq 1 ]; then
    # WARNING: Notificar pero no bloquear
    send_notification "WARNING: Ops Health audit detectó advertencias"
    exit 0
else
    # OK: No acción
    exit 0
fi
```

## Interpretación de Resultados

### Estado: OK
- ✅ Sistema saludable
- ✅ Todas las fuentes críticas monitoreadas
- ✅ No hay impactos críticos
- ✅ Coverage completo

**Acción:** Ninguna acción requerida.

### Estado: WARNING
- ⚠️ Hay advertencias pero no errores críticos
- ⚠️ Puede haber objetos no registrados
- ⚠️ Puede haber MVs sin refresh log

**Acción:** Revisar reporte y corregir advertencias en las próximas horas/días.

### Estado: CRITICAL
- ❌ Hay errores críticos
- ❌ Fuentes críticas sin monitoreo
- ❌ RAW stale afectando producción
- ❌ MVs fallidas o no pobladas

**Acción:** Revisar reporte inmediatamente y corregir errores críticos.

## Validación Manual

```bash
# Verificar que el script se ejecutó
ls -lh docs/backend/OPS_HEALTH_AUDIT_REPORT.*

# Ver resumen del reporte JSON
cat docs/backend/OPS_HEALTH_AUDIT_REPORT.json | jq '.summary'

# Ver checks fallidos
cat docs/backend/OPS_HEALTH_AUDIT_REPORT.json | jq '.checks[] | select(.status != "OK")'

# Ver objetos no registrados
cat docs/backend/OPS_HEALTH_AUDIT_REPORT.json | jq '.unregistered_used_objects'
```

## Troubleshooting

### Script falla en discovery

**Síntoma:** Exit code 2 en Fase 1

**Solución:**
- Verificar conexión a DB (`DATABASE_URL`)
- Verificar permisos de lectura en system catalogs
- Revisar logs del script discovery específico

### Registry no se puebla

**Síntoma:** Exit code 2 en Fase 2

**Solución:**
- Verificar que CSVs existan y tengan datos
- Verificar permisos de escritura en schema `ops`
- Revisar logs de `populate_source_registry.py`

### Validaciones fallan

**Síntoma:** Error en Fase 3

**Solución:**
- Verificar que vistas existan: `ops.v_health_checks`, `ops.v_health_global`
- Verificar que registry tenga datos
- Revisar traceback completo en logs

### Reportes no se generan

**Síntoma:** Fase 4 falla

**Solución:**
- Verificar permisos de escritura en `docs/backend/`
- Verificar espacio en disco
- Revisar logs para errores de I/O

## Principios

- ✅ **Automático:** No requiere intervención manual
- ✅ **Determinístico:** Mismos inputs → mismos outputs
- ✅ **Auditable:** Logs detallados y reportes completos
- ✅ **Seguro:** No modifica datos, solo lee y reporta
- ✅ **Idempotente:** Puede ejecutarse múltiples veces

## Referencias

- [Arquitectura del Sistema](OPS_HEALTH_SYSTEM_ARCHITECTURE.md)
- [Guía de Ejecución](OPS_HEALTH_EXECUTION_GUIDE.md)
- [Source Registry](source_registry.md)

