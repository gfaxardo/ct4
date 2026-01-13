# Scheduler: Cabinet 14d Jobs

**Última actualización:** 2024-12-19  
**Sistema:** CT4 - Cabinet 14d Auditable

---

## 1. JOBS A PROGRAMAR

### 1.1 reconcile_cabinet_claims_14d
**Frecuencia:** Diario a las 02:30  
**Propósito:** Generar claims faltantes cuando milestones fueron alcanzados

### 1.2 reconcile_cabinet_leads_pipeline
**Frecuencia:** Diario a las 02:30  
**Propósito:** Reconciliar leads en limbo (identity matching)

### 1.3 check_limbo_alerts
**Frecuencia:** Diario a las 02:30 (después de jobs)  
**Propósito:** Verificar umbrales y generar alertas

---

## 2. CONFIGURACIÓN CRON (Linux/Mac)

### 2.1 Editar crontab

```bash
crontab -e
```

### 2.2 Agregar entradas

```bash
# Cabinet 14d Jobs - Diario a las 02:30
30 2 * * * cd /ruta/al/proyecto/backend && source venv/bin/activate && python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000 >> /var/log/ct4/reconcile_claims.log 2>&1

30 2 * * * cd /ruta/al/proyecto/backend && source venv/bin/activate && python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000 >> /var/log/ct4/reconcile_leads.log 2>&1

35 2 * * * cd /ruta/al/proyecto/backend && source venv/bin/activate && python scripts/check_limbo_alerts.py >> /var/log/ct4/limbo_alerts.log 2>&1
```

**Nota:** Ajustar rutas según tu entorno.

### 2.3 Verificar crontab

```bash
crontab -l
```

---

## 3. CONFIGURACIÓN TASK SCHEDULER (Windows)

### 3.1 Crear tareas

1. Abrir **Task Scheduler** (Programador de tareas)
2. Crear tarea básica para cada job

#### Tarea 1: reconcile_cabinet_claims_14d

**General:**
- Nombre: `CT4 - Reconcile Cabinet Claims 14d`
- Descripción: `Generar claims faltantes cuando milestones fueron alcanzados`

**Trigger:**
- Tipo: Diario
- Hora: 02:30
- Repetir: Cada día

**Action:**
- Programa: `C:\ruta\al\proyecto\backend\venv\Scripts\python.exe`
- Argumentos: `-m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000`
- Directorio de inicio: `C:\ruta\al\proyecto\backend`

**Conditions:**
- Iniciar tarea solo si el equipo está conectado a la alimentación de CA: ✅
- Activar tarea solo si el equipo está conectado a la red: Opcional

**Settings:**
- Permitir ejecutar la tarea a petición: ✅
- Si la tarea falla, reiniciar cada: 10 minutos (máx 3 veces)

#### Tarea 2: reconcile_cabinet_leads_pipeline

**General:**
- Nombre: `CT4 - Reconcile Cabinet Leads Pipeline`
- Descripción: `Reconciliar leads en limbo (identity matching)`

**Trigger:**
- Tipo: Diario
- Hora: 02:30
- Repetir: Cada día

**Action:**
- Programa: `C:\ruta\al\proyecto\backend\venv\Scripts\python.exe`
- Argumentos: `-m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000`
- Directorio de inicio: `C:\ruta\al\proyecto\backend`

#### Tarea 3: check_limbo_alerts

**General:**
- Nombre: `CT4 - Check Limbo Alerts`
- Descripción: `Verificar umbrales y generar alertas`

**Trigger:**
- Tipo: Diario
- Hora: 02:35 (5 minutos después de jobs)
- Repetir: Cada día

**Action:**
- Programa: `C:\ruta\al\proyecto\backend\venv\Scripts\python.exe`
- Argumentos: `scripts/check_limbo_alerts.py`
- Directorio de inicio: `C:\ruta\al\proyecto\backend`

---

## 4. CONFIGURACIÓN CON SYSTEMD (Linux)

### 4.1 Crear servicio: reconcile_claims.service

```ini
[Unit]
Description=CT4 Reconcile Cabinet Claims 14d
After=network.target

[Service]
Type=oneshot
User=tu_usuario
WorkingDirectory=/ruta/al/proyecto/backend
Environment="PATH=/ruta/al/proyecto/backend/venv/bin"
ExecStart=/ruta/al/proyecto/backend/venv/bin/python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.2 Crear timer: reconcile_claims.timer

```ini
[Unit]
Description=Timer para CT4 Reconcile Cabinet Claims 14d
Requires=reconcile_claims.service

[Timer]
OnCalendar=daily
OnCalendar=02:30
Persistent=true

[Install]
WantedBy=timers.target
```

### 4.3 Activar timer

```bash
sudo systemctl enable reconcile_claims.timer
sudo systemctl start reconcile_claims.timer
sudo systemctl status reconcile_claims.timer
```

---

## 5. VERIFICACIÓN

### 5.1 Verificar que jobs corren

```bash
# Ver logs de cron
tail -f /var/log/ct4/reconcile_claims.log
tail -f /var/log/ct4/reconcile_leads.log
tail -f /var/log/ct4/limbo_alerts.log

# Ver historial de cron
grep CRON /var/log/syslog | tail -20
```

### 5.2 Verificar resultados

```bash
# Verificar que claims se generaron
python scripts/validate_claims_gap_before_after.py

# Verificar que limbo se redujo
python scripts/validate_limbo.py

# Verificar alertas
python scripts/check_limbo_alerts.py
```

---

## 6. MONITOREO Y ALERTAS

### 6.1 Integración con sistema de alertas

Los scripts de validación retornan exit codes:
- `0`: Todo OK
- `1`: Hay errores o alertas

Puedes integrar con:
- **Email:** Enviar email si exit code != 0
- **Slack/Teams:** Webhook si hay alertas
- **Monitoring:** Prometheus, Datadog, etc.

### 6.2 Ejemplo: Email alert

```bash
#!/bin/bash
# Script wrapper para enviar email si hay alertas

python scripts/check_limbo_alerts.py --output-json /tmp/limbo_alerts.json

if [ $? -ne 0 ]; then
    # Hay alertas, enviar email
    mail -s "CT4: Alertas de Limbo" admin@example.com < /tmp/limbo_alerts.json
fi
```

---

## 7. TROUBLESHOOTING

### 7.1 Job no corre

**Verificar:**
1. Crontab/Task Scheduler activo
2. Permisos de ejecución
3. Variables de entorno (DATABASE_URL)
4. Logs de errores

### 7.2 Job falla

**Verificar:**
1. Conexión a base de datos
2. Vistas SQL desplegadas
3. Dependencias instaladas
4. Logs detallados

---

**NOTA:** Ajustar rutas y configuración según tu entorno específico.
