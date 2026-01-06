# CT4 Ops Health — Quick Start

## Ejecución Rápida (3 Pasos)

### 1️⃣ Activar Entorno Virtual

```powershell
cd C:\cursor\CT4
.\backend\venv\Scripts\Activate.ps1
```

### 2️⃣ Ejecutar Auditoría

```bash
python backend/scripts/run_ops_health_audit.py
```

### 3️⃣ Revisar Reportes

```powershell
# Reporte legible
notepad docs\backend\OPS_HEALTH_AUDIT_REPORT.md

# Reporte JSON (formateado)
Get-Content docs\backend\OPS_HEALTH_AUDIT_REPORT.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

## Interpretación Rápida

| Exit Code | Estado | Significado |
|-----------|--------|-------------|
| `0` | ✅ OK | Sistema saludable |
| `1` | ⚠️ WARNING | Hay advertencias |
| `2` | ❌ CRITICAL | Errores críticos |

**Verificar exit code:**
```powershell
echo $LASTEXITCODE
```

---

## Troubleshooting Rápido

| Error | Solución |
|-------|----------|
| `No module named 'pydantic_settings'` | `pip install -r backend/requirements.txt` |
| `DATABASE_URL no está definida` | Verificar `backend/app/config.py` o definir variable de entorno |
| `discovery_objects.py falló` | Ejecutar manualmente: `python backend/scripts/discovery_objects.py` |
| `UnicodeEncodeError` | Ya manejado automáticamente, si persiste: `chcp 65001` |

---

## Archivos Generados

```
docs/backend/
├── OPS_HEALTH_AUDIT_REPORT.md    ← Reporte legible (Markdown)
└── OPS_HEALTH_AUDIT_REPORT.json  ← Reporte estructurado (JSON)

backend/sql/ops/
├── discovery_objects.csv          ← Objetos DB descubiertos
├── discovery_dependencies.csv     ← Dependencias descubiertas
└── discovery_usage_backend.csv   ← Uso en código descubierto
```

---

## Comandos Útiles

```powershell
# Verificar que estás en el venv correcto
python --version
pip list | findstr "sqlalchemy"

# Ejecutar discovery individual
python backend/scripts/discovery_objects.py
python backend/scripts/discovery_dependencies.py
python backend/scripts/discovery_usage_backend.py

# Poblar registry manualmente
python backend/scripts/populate_source_registry.py

# Ver reportes
notepad docs\backend\OPS_HEALTH_AUDIT_REPORT.md
```

---

## Documentación Completa

- [Guía Paso a Paso Detallada](OPS_HEALTH_AUDIT_MANUAL_STEPS.md)
- [Documentación del Script](OPS_HEALTH_AUDIT_SCRIPT.md)
- [Arquitectura del Sistema](OPS_HEALTH_SYSTEM_ARCHITECTURE.md)







