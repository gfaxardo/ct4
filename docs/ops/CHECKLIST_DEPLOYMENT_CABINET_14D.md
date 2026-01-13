# Checklist de Deployment - Sistema Auditable Cabinet 14d

**Fecha:** 2024-12-19  
**Sistema:** CT4 - Cabinet 14d Auditable

---

## PRE-DEPLOYMENT

### 1. Verificar Base de Datos
- [ ] Base de datos accesible
- [ ] Schema `ops` existe
- [ ] Schema `canon` existe
- [ ] Tablas RAW existen:
  - [ ] `public.module_ct_cabinet_leads`
  - [ ] `public.summary_daily`
  - [ ] `canon.identity_links`
  - [ ] `canon.claims_yango_cabinet_14d`

### 2. Verificar Migraciones
- [ ] Alembic configurado
- [ ] Última migración: `019_fix_claims_gap_expected_amount`
- [ ] Ejecutar migraciones:
  ```bash
  cd backend
  alembic upgrade head
  ```

### 3. Verificar Vistas SQL
- [ ] `ops.v_cabinet_leads_limbo` existe
- [ ] `ops.v_cabinet_claims_expected_14d` existe
- [ ] `ops.v_cabinet_claims_gap_14d` existe y tiene columna `expected_amount`

**Query de verificación:**
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_schema = 'ops' 
  AND table_name = 'v_cabinet_claims_gap_14d' 
  AND column_name = 'expected_amount';
```

---

## DEPLOYMENT

### 4. Desplegar Backend
- [ ] Código actualizado
- [ ] Dependencias instaladas:
  ```bash
  cd backend
  pip install -r requirements.txt
  ```
- [ ] Variables de entorno configuradas:
  - [ ] `DATABASE_URL`
- [ ] Servidor inicia sin errores:
  ```bash
  uvicorn app.main:app --reload
  ```

### 5. Desplegar Frontend
- [ ] Código actualizado
- [ ] Dependencias instaladas:
  ```bash
  cd frontend
  npm install
  ```
- [ ] Build exitoso:
  ```bash
  npm run build
  ```
- [ ] Servidor inicia sin errores:
  ```bash
  npm run dev
  ```

### 6. Verificar Endpoints
- [ ] Endpoint Limbo funciona:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/limbo?limit=1"
  ```
- [ ] Endpoint Claims Gap funciona:
  ```bash
  curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/claims-gap?limit=1"
  ```
- [ ] No hay error 500

---

## POST-DEPLOYMENT

### 7. Validación End-to-End
- [ ] Ejecutar validación completa:
  ```bash
  python scripts/validate_system_end_to_end.py
  ```
- [ ] Todos los checks pasan

### 8. Validación de Reglas Duras
- [ ] Validar Limbo:
  ```bash
  python scripts/validate_limbo.py
  ```
- [ ] Validar Claims Gap:
  ```bash
  python scripts/validate_claims_gap_before_after.py
  ```
- [ ] No hay violaciones

### 9. Verificar Alertas
- [ ] Ejecutar check de alertas:
  ```bash
  python scripts/check_limbo_alerts.py
  ```
- [ ] Umbrales configurados correctamente

### 10. Probar Jobs Manualmente
- [ ] Probar reconcile_cabinet_claims_14d (dry-run):
  ```bash
  python -m jobs.reconcile_cabinet_claims_14d --only-gaps --dry-run --limit 10
  ```
- [ ] Probar reconcile_cabinet_leads_pipeline (dry-run):
  ```bash
  python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --dry-run --limit 10
  ```

---

## CONFIGURACIÓN DE PRODUCCIÓN

### 11. Configurar Scheduler
- [ ] Cron/Task Scheduler configurado (ver `docs/runbooks/scheduler_cabinet_14d.md`)
- [ ] Jobs programados:
  - [ ] `reconcile_cabinet_claims_14d` (diario 02:30)
  - [ ] `reconcile_cabinet_leads_pipeline` (diario 02:30)
  - [ ] `check_limbo_alerts` (diario 02:35)
- [ ] Logs configurados

### 12. Configurar Alertas
- [ ] Sistema de alertas configurado (email/Slack/Teams)
- [ ] Umbrales definidos:
  - [ ] `limbo_no_identity` > 100
  - [ ] `pct_with_identity` < 80%
  - [ ] `TRIPS_NO_CLAIM` > 0 por 3 días

### 13. Documentación
- [ ] Runbook accesible: `docs/runbooks/limbo_and_claims_gap.md`
- [ ] Scheduler documentado: `docs/runbooks/scheduler_cabinet_14d.md`
- [ ] Equipo entrenado en uso del sistema

---

## VALIDACIÓN FINAL

### 14. Smoke Tests
- [ ] UI Limbo carga correctamente
- [ ] UI Claims Gap carga correctamente
- [ ] Filtros funcionan
- [ ] Export CSV funciona
- [ ] Totales se muestran correctamente

### 15. Pruebas de Integración
- [ ] Job de claims genera claims faltantes
- [ ] Job de leads reduce limbo
- [ ] Alertas se generan cuando corresponde

---

## ROLLBACK (si es necesario)

### 16. Plan de Rollback
- [ ] Revertir migración:
  ```bash
  alembic downgrade -1
  ```
- [ ] Restaurar código anterior
- [ ] Verificar que sistema anterior funciona

---

## NOTAS

- Ejecutar este checklist en orden
- Marcar cada item cuando se complete
- Documentar cualquier problema encontrado
- Si hay errores, no continuar hasta resolverlos

---

**Última actualización:** 2024-12-19
