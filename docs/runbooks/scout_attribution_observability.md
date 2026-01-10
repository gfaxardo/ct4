# Runbook: Scout Attribution Observability

**Última actualización**: 2025-01-09  
**Versión**: 1.0

---

## 📋 Índice

1. [Objetivo](#objetivo)
2. [Arquitectura](#arquitectura)
3. [Setup del Job Recurrente](#setup-del-job-recurrente)
4. [Verificación de Salud](#verificación-de-salud)
5. [Troubleshooting](#troubleshooting)
6. [Auditoría](#auditoría)
7. [Límites y Garantías](#límites-y-garantías)

---

## 🎯 Objetivo

Sistema de observabilidad y auto-refresh para atribución de scouts que:
- Mantiene `identity_links` actualizados para `scouting_daily`
- Propaga scouts desde `lead_events` a `lead_ledger` cuando es único
- Proporciona métricas en tiempo real de salud del sistema
- Genera alertas para casos que requieren revisión manual

**NO afecta**: Cobro Yango, claims-to-collect, ni pagos existentes.

---

## 🏗️ Arquitectura

### Componentes

1. **Vistas SQL de Métricas**:
   - `ops.v_scout_attribution_metrics_snapshot` - Métricas instantáneas
   - `ops.v_scout_attribution_metrics_daily` - Tendencia histórica (30 días)

2. **Vistas Canónicas**:
   - `ops.v_scout_attribution_raw` - Fuentes unificadas
   - `ops.v_scout_attribution` - Scout canónico por persona
   - `ops.v_scout_attribution_conflicts` - Conflictos (múltiples scouts)
   - `ops.v_persons_without_scout_categorized` - Backlog categorizado (A/C/D)
   - `ops.v_yango_collection_with_scout` - Cobranza Yango extendida

3. **Tablas de Auditoría (Append-Only)**:
   - `ops.identity_links_backfill_audit` - Backfills de identity_links
   - `ops.lead_ledger_scout_backfill_audit` - Backfills de lead_ledger
   - `ops.lead_events_scout_backfill_audit` - Backfills de lead_events
   - `ops.job_runs_audit` / `ops.ingestion_runs` - Ejecuciones de jobs

4. **Scripts**:
   - `backend/scripts/run_scout_attribution_refresh.py` - Run once
   - `backend/scripts/ops_refresh_scout_attribution.py` - Job recurrente
   - `backend/scripts/ops_refresh_scout_attribution.ps1` - Job recurrente (Windows)

5. **API Endpoints**:
   - `GET /api/v1/scouts/attribution/metrics` - Métricas instantáneas
   - `GET /api/v1/scouts/attribution/metrics/daily` - Métricas históricas
   - `GET /api/v1/scouts/attribution/conflicts` - Lista conflictos
   - `GET /api/v1/scouts/attribution/backlog` - Backlog por categorías
   - `GET /api/v1/scouts/attribution/job-status` - Estado del job
   - `POST /api/v1/scouts/attribution/run-now` - Trigger manual

6. **Frontend UI**:
   - `/scouts/attribution-health` - Dashboard principal con auto-refresh
   - `/scouts/conflicts` - Lista de conflictos
   - `/scouts/backlog` - Backlog por categorías
   - `/scouts/cobranza-yango` - Cobranza Yango con scout
   - `/scouts/liquidation` - Vista base de liquidación

---

## ⚙️ Setup del Job Recurrente

### Opción A: Linux (Cron)

1. **Usar script de configuración**:
```bash
cd backend/scripts
chmod +x setup_recurrent_job.sh
./setup_recurrent_job.sh
```

O manualmente:

1. **Crear script ejecutable**:
```bash
chmod +x backend/scripts/ops_refresh_scout_attribution.py
```

2. **Agregar a crontab** (ejecutar cada 4 horas):
```bash
crontab -e

# Agregar línea:
0 */4 * * * cd /path/to/CT4 && python backend/scripts/ops_refresh_scout_attribution.py >> /var/log/scout_refresh.log 2>&1
```

3. **Verificar ejecución**:
```bash
tail -f /var/log/scout_refresh.log
```

### Opción B: Windows (Task Scheduler)

1. **Usar script de configuración**:
```powershell
cd backend\scripts
.\setup_recurrent_job.ps1
```

O manualmente:

1. **Abrir Task Scheduler** (tareaschd.msc)

2. **Crear tarea básica**:
   - Nombre: "Scout Attribution Refresh"
   - Trigger: Repetir cada 4 horas
   - Acción: Iniciar programa
   - Programa: `powershell.exe`
   - Argumentos: `-File "C:\path\to\CT4\backend\scripts\ops_refresh_scout_attribution.ps1"`

3. **Verificar ejecución**:
   - Ver historial en Task Scheduler

### Opción C: Docker Compose Service

Si el proyecto usa docker-compose, agregar servicio:

```yaml
services:
  scout-refresh:
    build: ./backend
    command: python backend/scripts/ops_refresh_scout_attribution.py
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
    restart: unless-stopped
    # Nota: requeriría scheduler externo (ej: cron dentro del container) para cada 4h
```

---

## ✅ Verificación de Salud

### 1. UI de Observabilidad

Acceder a: `http://localhost:3000/scouts/attribution-health`

**Indicadores de salud**:
- ✅ **OK**: Scout satisfactorio > 80%, conflictos < 50, job ejecutado < 1 hora
- ⚠️ **WARN**: Scout satisfactorio 50-80%, conflictos 50-100, job ejecutado > 4 horas
- ❌ **FAIL**: Scout satisfactorio < 50%, conflictos > 100, job fallido

### 2. Verificación Manual (SQL)

```sql
-- Métricas instantáneas
SELECT * FROM ops.v_scout_attribution_metrics_snapshot;

-- Verificar última ejecución del job
SELECT 
    id,
    job_type,
    status,
    started_at,
    completed_at,
    error_message
FROM ops.ingestion_runs
WHERE job_type = 'scout_attribution_refresh'
ORDER BY started_at DESC
LIMIT 5;

-- Verificar conflictos
SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts;

-- Verificar backlog por categoría
SELECT 
    category,
    COUNT(*) as count
FROM ops.v_persons_without_scout_categorized
GROUP BY category;
```

### 3. Verificación de Backfills

```sql
-- Identity links backfill (últimas 24h)
SELECT 
    action_type,
    COUNT(*) as count
FROM ops.identity_links_backfill_audit
WHERE backfill_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY action_type;

-- Lead ledger backfill (últimas 24h)
SELECT 
    COUNT(*) as updated_count
FROM ops.lead_ledger_scout_backfill_audit
WHERE backfill_timestamp >= NOW() - INTERVAL '24 hours';
```

---

## 🔧 Troubleshooting

### Problema: Job no se ejecuta

**Verificar**:
1. ¿Existe el registro en cron/Task Scheduler?
2. ¿Tiene permisos de ejecución el script?
3. ¿Está la base de datos accesible?

**Solución**:
```bash
# Ejecutar manualmente para ver errores
python backend/scripts/run_scout_attribution_refresh.py
```

### Problema: Job falla con error de conexión

**Verificar**:
1. Variable de entorno `DATABASE_URL` configurada
2. Base de datos accesible desde el host
3. Credenciales correctas

**Solución**:
```bash
# Verificar conexión
python -c "from app.db import SessionLocal; db = SessionLocal(); db.execute(text('SELECT 1')); db.close()"
```

### Problema: % Scout satisfactorio bajo

**Verificar**:
1. ¿Hay muchos registros sin identity_links?
2. ¿Hay muchos conflictos?
3. ¿El job está ejecutándose correctamente?

**Acción**:
1. Revisar backlog por categorías en UI
2. Ejecutar backfill manual si es necesario
3. Revisar conflictos para resolución manual

### Problema: Conflictos creciendo

**Causa probable**: Nuevos registros con múltiples scouts o datos inconsistentes.

**Acción**:
1. Revisar conflictos en `/scouts/conflicts`
2. Investigar fuentes de los conflictos
3. Resolver manualmente asignando scout correcto en `lead_ledger`

### Problema: Vista no existe

**Solución**:
```sql
-- Ejecutar scripts SQL en orden:
-- 1. backend/scripts/sql/00_inventory_scout_sources.sql
-- 2. backend/scripts/sql/20_create_audit_tables.sql
-- 3. backend/scripts/sql/01_metrics_scout_attribution.sql
-- 4. backend/scripts/sql/02-07_create_v_*.sql (vistas canónicas)
```

---

## 📊 Auditoría

### ¿Qué se audita?

1. **Todos los backfills** quedan registrados en tablas append-only
2. **Ejecuciones de jobs** quedan en `ops.ingestion_runs` o `ops.job_runs_audit`
3. **Cambios en lead_ledger** quedan en `ops.lead_ledger_scout_backfill_audit`

### Consultas de Auditoría

```sql
-- Ver todos los backfills de identity_links (último mes)
SELECT 
    source_table,
    action_type,
    COUNT(*) as count,
    MIN(backfill_timestamp) as first_backfill,
    MAX(backfill_timestamp) as last_backfill
FROM ops.identity_links_backfill_audit
WHERE backfill_timestamp >= NOW() - INTERVAL '30 days'
GROUP BY source_table, action_type
ORDER BY last_backfill DESC;

-- Ver todos los backfills de lead_ledger (último mes)
SELECT 
    backfill_method,
    COUNT(*) as updated_count,
    MIN(backfill_timestamp) as first_backfill,
    MAX(backfill_timestamp) as last_backfill
FROM ops.lead_ledger_scout_backfill_audit
WHERE backfill_timestamp >= NOW() - INTERVAL '30 days'
GROUP BY backfill_method
ORDER BY last_backfill DESC;

-- Ver historial de ejecuciones del job
SELECT 
    id,
    status,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at))::INTEGER as duration_seconds,
    error_message
FROM ops.ingestion_runs
WHERE job_type = 'scout_attribution_refresh'
ORDER BY started_at DESC
LIMIT 20;
```

### Reversión de Cambios

**⚠️ IMPORTANTE**: Los backfills son **idempotentes** pero **NO reversibles automáticamente**.

Si necesitas revertir un backfill:
1. Consultar tabla de auditoría para ver qué se cambió
2. Revertir manualmente en `lead_ledger` si es necesario
3. Registrar motivo de reversión en notas

---

## 🛡️ Límites y Garantías

### Límites

1. **No inventa scouts**: Si hay conflicto (>1 scout), NO toca el registro
2. **Solo backfill incremental**: No recalcula identity globalmente, solo nuevas filas
3. **Idempotente**: Se puede ejecutar múltiples veces sin duplicar cambios
4. **No afecta claims Yango**: Solo lee vistas existentes, no modifica lógica de cobranza

### Garantías

1. **Auditable**: Todo cambio queda registrado en tablas append-only
2. **Seguro**: Solo actualiza cuando hay evidencia inequívoca (1 scout único)
3. **Transparente**: Todas las métricas y estados visibles en UI
4. **Recuperable**: Se puede ejecutar manualmente o revertir cambios si es necesario

### No Garantiza

1. **Resolución automática de conflictos**: Requiere revisión manual
2. **100% cobertura de scout**: Pueden quedar casos legacy o sin eventos
3. **Backfill de cabinet_leads**: Solo si existe mapping 1:1 confiable (actualmente no implementado)

---

## 🚀 Ejecución Manual

### Ejecutar Refresh Ahora

**Desde UI**:
1. Ir a `/scouts/attribution-health`
2. Click en "Ejecutar ahora"

**Desde API**:
```bash
curl -X POST http://localhost:8000/api/v1/scouts/attribution/run-now
```

**Desde Script**:
```bash
python backend/scripts/run_scout_attribution_refresh.py
```

---

## 📞 Contacto y Soporte

Para problemas o preguntas:
1. Revisar este runbook
2. Consultar logs del job
3. Revisar tablas de auditoría
4. Consultar UI de observabilidad

**Nunca modificar directamente**:
- `ops.*_audit` (append-only)
- Lógica de cobranza Yango
- Tablas canónicas sin auditoría

---

**✅ Sistema listo para operación diaria**

