# Ejecución: Próximos Pasos Recovery Impact

## ✅ Resumen

Se han creado los scripts necesarios para ejecutar los próximos pasos del sistema de Recovery Impact. **IMPORTANTE:** La migración debe ejecutarse **PRIMERO** antes de crear las vistas SQL.

---

## 📋 Orden de Ejecución (CRÍTICO)

### ⚠️ PASO 1: Ejecutar Migración (OBLIGATORIO PRIMERO)

**Windows PowerShell:**
```powershell
cd backend
alembic upgrade head
```

**Verificación:**
- Debe crear la tabla `ops.cabinet_lead_recovery_audit`
- Debe mostrar mensajes de éxito de Alembic

**⚠️ NOTA:** Sin esta migración, la vista `v_cabinet_identity_recovery_impact_14d` NO puede crearse porque depende de la tabla `ops.cabinet_lead_recovery_audit`.

---

### ✅ PASO 2: Crear Vistas SQL (DESPUÉS de la migración)

**Windows PowerShell:**
```powershell
cd backend
python execute_recovery_impact_steps.py
```

**O manualmente con psql:**
```powershell
# Vista 1
psql -h 168.119.226.236 -U yego_user -d yego_integral -f sql/ops/v_cabinet_lead_identity_effective.sql

# Vista 2 (requiere que la migración ya se haya ejecutado)
psql -h 168.119.226.236 -U yego_user -d yego_integral -f sql/ops/v_cabinet_identity_recovery_impact_14d.sql
```

**Verificación:**
- Script debe mostrar: "[OK] Vista v_cabinet_lead_identity_effective creada exitosamente"
- Script debe mostrar: "[OK] Vista v_cabinet_identity_recovery_impact_14d creada exitosamente"

**⚠️ NOTA:** Si la migración no se ejecutó, la segunda vista fallará con error: `relation "ops.cabinet_lead_recovery_audit" does not exist`

---

### ✅ PASO 3: Probar Endpoint

**Con el servidor corriendo:**
```bash
curl "http://localhost:8000/api/v1/yango/cabinet/identity-recovery-impact-14d?include_series=false"
```

**O desde Python (si el servidor no está corriendo):**
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get('/api/v1/yango/cabinet/identity-recovery-impact-14d?include_series=false')
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
```

**Verificación:**
- Status debe ser 200
- Response debe contener: `totals`, `series` (opcional), `top_reasons` (opcional)

---

### ⚠️ PASO 4: Ejecutar Job (Opcional)

**Windows PowerShell:**
```powershell
cd backend
python -m jobs.cabinet_recovery_impact_job 1000
```

**Propósito:**
- Procesar leads "unidentified" o "identified_no_origin"
- Crear/actualizar `canon.identity_origin` con `origin_tag='cabinet_lead'`
- Registrar en `ops.cabinet_lead_recovery_audit`

**Verificación:**
- Debe mostrar estadísticas: processed, origins_created, origins_updated, audit_created, audit_updated

---

### ✅ PASO 5: Verificar

**Queries de verificación:**
Ver archivo: `docs/ops/verify_cabinet_recovery_impact.md`

**Verificación rápida:**
```sql
-- Verificar que las vistas existen
SELECT viewname 
FROM pg_views 
WHERE schemaname = 'ops' 
AND viewname IN ('v_cabinet_lead_identity_effective', 'v_cabinet_identity_recovery_impact_14d');

-- Verificar que la tabla existe
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'ops' 
AND table_name = 'cabinet_lead_recovery_audit';

-- Verificar datos en las vistas
SELECT COUNT(*) FROM ops.v_cabinet_lead_identity_effective;
SELECT COUNT(*) FROM ops.v_cabinet_identity_recovery_impact_14d;
```

---

## ✅ Estado Final Esperado

Después de ejecutar todos los pasos en orden:

- ✅ **Migración:** Tabla `ops.cabinet_lead_recovery_audit` creada
- ✅ **Vistas:** `ops.v_cabinet_lead_identity_effective` y `ops.v_cabinet_identity_recovery_impact_14d` creadas
- ✅ **Endpoint:** `GET /api/v1/yango/cabinet/identity-recovery-impact-14d` funcionando
- ⚠️ **Job:** Pendiente de ejecución (opcional)
- ⚠️ **UI:** Pendiente de integración

---

## 📝 Notas Importantes

1. **⚠️ ORDEN CRÍTICO:** La migración DEBE ejecutarse ANTES de crear las vistas SQL, porque la vista `v_cabinet_identity_recovery_impact_14d` depende de la tabla `ops.cabinet_lead_recovery_audit`.

2. **El script Python solo crea las vistas SQL.** La migración debe ejecutarse manualmente con `alembic upgrade head`.

3. **El job es opcional:** Puede ejecutarse cuando se necesite procesar leads sin identidad/origin.

4. **El job es idempotente:** Puede ejecutarse múltiples veces sin romper nada.

5. **No destructivo:** Solo crea/actualiza, nunca elimina.

6. **Recovery solo puede:**
   - Crear vínculo canónico entre Lead Cabinet y person_key existente (via canon.identity_links)
   - Upsert canon.identity_origin (cabinet_lead + origin_source_id=lead_id)
   - Registrar en ops.cabinet_lead_recovery_audit

---

## 🎉 Conclusión

Los scripts están listos para ejecutarse. **EJECUTA LA MIGRACIÓN PRIMERO**, luego crea las vistas SQL. Sigue los pasos en orden para completar la implementación del sistema de Recovery Impact.
