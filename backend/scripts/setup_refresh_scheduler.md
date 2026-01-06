# Configurar Refresh Automático de Vista Materializada

## Opción 1: Cron Job (Linux/Mac) - RECOMENDADO

### Configurar Cron
```bash
# Editar crontab
crontab -e

# Agregar línea (refresh cada hora a las :00)
0 * * * * cd /path/to/CT4 && /path/to/psql $DATABASE_URL -f backend/scripts/sql/refresh_mv_driver_matrix.sql >> /var/log/refresh_mv_driver_matrix.log 2>&1
```

### O usar script Python
```bash
# Agregar a crontab
0 * * * * cd /path/to/CT4 && /path/to/python backend/scripts/refresh_mv_driver_matrix_scheduled.py >> /var/log/refresh_mv_driver_matrix.log 2>&1
```

## Opción 2: Task Scheduler (Windows)

### Pasos:
1. Abrir "Programador de tareas" (Task Scheduler)
2. Crear tarea básica
3. **General:**
   - Nombre: "Refresh Driver Matrix MV"
   - Ejecutar con privilegios más altos: ✅
4. **Triggers:**
   - Nueva → Diariamente
   - Repetir cada: 1 hora
   - Duración: Indefinidamente
5. **Acciones:**
   - Iniciar programa
   - Programa: `C:\Program Files\PostgreSQL\18\bin\psql.exe`
   - Argumentos: `$DATABASE_URL -f C:\path\to\CT4\backend\scripts\sql\refresh_mv_driver_matrix.sql`
   - Iniciar en: `C:\path\to\CT4`

### O usar script Python
```powershell
# En Task Scheduler
# Programa: python
# Argumentos: C:\path\to\CT4\backend\scripts\refresh_mv_driver_matrix_scheduled.py
```

## Opción 3: Script Python con APScheduler (Producción)

### Instalar dependencias
```bash
pip install apscheduler
```

### Crear script scheduler
```python
# backend/scripts/scheduler_refresh_mv.py
from apscheduler.schedulers.blocking import BlockingScheduler
from refresh_mv_driver_matrix_scheduled import refresh_materialized_view

scheduler = BlockingScheduler()

# Ejecutar cada hora
scheduler.add_job(
    refresh_materialized_view,
    'interval',
    hours=1,
    id='refresh_mv_driver_matrix',
    name='Refresh Driver Matrix Materialized View',
    replace_existing=True
)

if __name__ == "__main__":
    print("Scheduler iniciado. Refresh cada hora.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
```

### Ejecutar
```bash
python backend/scripts/scheduler_refresh_mv.py
```

## Opción 4: Celery (Si ya está en uso)

### Crear tarea Celery
```python
# backend/app/tasks/refresh_mv.py
from celery import shared_task
from scripts.refresh_mv_driver_matrix_scheduled import refresh_materialized_view

@shared_task
def refresh_driver_matrix_mv():
    """Tarea Celery para refrescar vista materializada"""
    return refresh_materialized_view()
```

### Configurar beat schedule
```python
# backend/app/celery_app.py
from celery.schedules import crontab

beat_schedule = {
    'refresh-driver-matrix-mv': {
        'task': 'app.tasks.refresh_mv.refresh_driver_matrix_mv',
        'schedule': crontab(minute=0),  # Cada hora
    },
}
```

## Verificación

### Verificar último refresh
```sql
-- La vista materializada no tiene timestamp automático
-- Revisar logs para saber cuándo se actualizó
```

### Probar refresh manual
```bash
# SQL directo
psql $DATABASE_URL -f backend/scripts/sql/refresh_mv_driver_matrix.sql

# O script Python
python backend/scripts/refresh_mv_driver_matrix_scheduled.py
```

## Frecuencia Recomendada

- **Producción:** Cada hora (0 * * * *)
- **Desarrollo:** Según necesidad (manual o cada 6 horas)
- **Testing:** Manual cuando sea necesario

## Monitoreo

### Verificar logs
```bash
# Linux/Mac
tail -f /var/log/refresh_mv_driver_matrix.log

# Windows
# Ver logs en Task Scheduler o archivo de log configurado
```

### Alertas
- Configurar alerta si refresh falla
- Monitorear tiempo de refresh (debe ser < 5 minutos)
- Alertar si vista materializada tiene > 2 horas sin actualizar

