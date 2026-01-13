# Ejecutar Pasos Recovery Impact - Guía Rápida

## ⚠️ IMPORTANTE: Orden de Ejecución

**La migración DEBE ejecutarse PRIMERO antes de crear las vistas SQL.**

---

## Paso 1: Ejecutar Migración (OBLIGATORIO PRIMERO)

```powershell
cd backend
alembic upgrade head
```

**Verificar que funcionó:**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'ops' 
AND table_name = 'cabinet_lead_recovery_audit';
```

Debe retornar 1 fila.

---

## Paso 2: Crear Vistas SQL

```powershell
cd backend
python execute_recovery_impact_steps.py
```

**O manualmente:**
```powershell
psql -h 168.119.226.236 -U yego_user -d yego_integral -f sql/ops/v_cabinet_lead_identity_effective.sql
psql -h 168.119.226.236 -U yego_user -d yego_integral -f sql/ops/v_cabinet_identity_recovery_impact_14d.sql
```

---

## Paso 3: Verificar

```sql
-- Verificar vistas
SELECT viewname FROM pg_views WHERE schemaname = 'ops' AND viewname IN ('v_cabinet_lead_identity_effective', 'v_cabinet_identity_recovery_impact_14d');

-- Contar registros
SELECT COUNT(*) FROM ops.v_cabinet_lead_identity_effective;
SELECT COUNT(*) FROM ops.v_cabinet_identity_recovery_impact_14d;
```

---

## Paso 4: Probar Endpoint (Opcional)

```bash
curl "http://localhost:8000/api/v1/yango/cabinet/identity-recovery-impact-14d?include_series=false"
```

---

## Paso 5: Ejecutar Job (Opcional)

```powershell
cd backend
python -m jobs.cabinet_recovery_impact_job 1000
```
