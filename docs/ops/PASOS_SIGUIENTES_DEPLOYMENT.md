# Pasos Siguientes - Deployment y Validación

**Fecha:** 2024-12-19  
**Estado:** Listo para deployment

---

## RESUMEN DE LO COMPLETADO

✅ **PASO 1:** Inventario real - Endpoints, vistas SQL y columnas identificadas  
✅ **PASO 2:** Fix Claims Gap - Error `expected_amount` corregido  
✅ **PASO 3:** Limbo implementado - Reglas duras validadas  
✅ **PASO 4:** Jobs - Scripts de validación creados  
✅ **PASO 5:** Scheduler + alertas + runbook - Documentación completa  

---

## PASOS SIGUIENTES (ORDEN DE EJECUCIÓN)

### PASO 6: Ejecutar Migración

```bash
cd backend
alembic upgrade head
```

**Verificar:**
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_schema = 'ops' 
  AND table_name = 'v_cabinet_claims_gap_14d' 
  AND column_name = 'expected_amount';
```

**Resultado esperado:** 1 fila (columna existe)

---

### PASO 7: Validación End-to-End

```bash
# Validación completa del sistema
python scripts/validate_system_end_to_end.py

# Si el servidor no está corriendo, usar --skip-ui
python scripts/validate_system_end_to_end.py --skip-ui
```

**Qué valida:**
- ✅ Vistas SQL existen y son accesibles
- ✅ Reglas duras cumplidas
- ✅ Endpoints funcionan (opcional)
- ✅ Jobs importables
- ✅ Scripts de validación existen

---

### PASO 8: Validación Individual

```bash
# 1. Validar Limbo
python scripts/validate_limbo.py

# 2. Validar Claims Gap
python scripts/validate_claims_gap_before_after.py

# 3. Verificar alertas
python scripts/check_limbo_alerts.py
```

**Resultado esperado:** Todos los checks pasan (exit code 0)

---

### PASO 9: Probar Endpoints

```bash
# 1. Probar endpoint Limbo
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/limbo?limit=10"

# 2. Probar endpoint Claims Gap
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/claims-gap?limit=10"
```

**Resultado esperado:** Status 200, JSON válido, sin error 500

---

### PASO 10: Probar Jobs (Dry-Run)

```bash
# 1. Probar reconcile_cabinet_claims_14d
python -m jobs.reconcile_cabinet_claims_14d --only-gaps --dry-run --limit 10

# 2. Probar reconcile_cabinet_leads_pipeline
python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --dry-run --limit 10
```

**Resultado esperado:** Jobs ejecutan sin errores, muestran qué procesarían

---

### PASO 11: Probar UI

1. Iniciar servidor backend:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Iniciar servidor frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Navegar a:
   - `http://localhost:3000/pagos/cobranza-yango`
   - Verificar que secciones "Leads en Limbo" y "Claims Gap" cargan
   - Probar filtros
   - Probar export CSV

---

### PASO 12: Configurar Scheduler

**Opción A: Cron (Linux/Mac)**
```bash
crontab -e

# Agregar:
30 2 * * * cd /ruta/al/proyecto/backend && source venv/bin/activate && python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000 >> /var/log/ct4/reconcile_claims.log 2>&1
30 2 * * * cd /ruta/al/proyecto/backend && source venv/bin/activate && python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000 >> /var/log/ct4/reconcile_leads.log 2>&1
35 2 * * * cd /ruta/al/proyecto/backend && source venv/bin/activate && python scripts/check_limbo_alerts.py >> /var/log/ct4/limbo_alerts.log 2>&1
```

**Opción B: Task Scheduler (Windows)**
- Seguir instrucciones en `docs/runbooks/scheduler_cabinet_14d.md`

---

### PASO 13: Ejecutar Jobs en Producción (Primera Vez)

```bash
# 1. Reconciliar claims (sin dry-run)
python -m jobs.reconcile_cabinet_claims_14d --only-gaps --limit 1000

# 2. Reconciliar leads (sin dry-run)
python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 500

# 3. Verificar resultados
python scripts/validate_limbo.py
python scripts/validate_claims_gap_before_after.py
```

---

### PASO 14: Monitoreo Inicial

**Primera semana:**
- [ ] Verificar logs diarios de jobs
- [ ] Verificar que alertas funcionan
- [ ] Monitorear métricas:
  - `limbo_no_identity`
  - `pct_with_identity`
  - `TRIPS_NO_CLAIM`
- [ ] Revisar que claims se generan correctamente

---

## CHECKLIST RÁPIDO

- [ ] Migración ejecutada
- [ ] Validación end-to-end pasa
- [ ] Endpoints funcionan (200, sin error 500)
- [ ] UI carga correctamente
- [ ] Jobs ejecutan sin errores
- [ ] Scheduler configurado
- [ ] Alertas configuradas
- [ ] Documentación accesible

---

## TROUBLESHOOTING RÁPIDO

### Error: "expected_amount no existe"
**Solución:** Ejecutar migración `019_fix_claims_gap_expected_amount`

### Error 500 en Claims Gap
**Solución:** Verificar que migración se ejecutó y columna existe

### Jobs no corren
**Solución:** Verificar scheduler, permisos, variables de entorno

### UI no carga
**Solución:** Verificar que backend está corriendo y accesible

---

## DOCUMENTACIÓN DE REFERENCIA

- **Runbook:** `docs/runbooks/limbo_and_claims_gap.md`
- **Scheduler:** `docs/runbooks/scheduler_cabinet_14d.md`
- **Checklist Deployment:** `docs/ops/CHECKLIST_DEPLOYMENT_CABINET_14D.md`
- **Inventario:** `docs/ops/PASO1_INVENTARIO_CABINET_14D.md`

---

**NOTA:** Ejecutar estos pasos en orden. Si algún paso falla, no continuar hasta resolverlo.
