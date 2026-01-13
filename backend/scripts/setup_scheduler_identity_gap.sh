#!/bin/bash
# Script para configurar scheduler del Identity Gap Recovery Job
# Ejecutar como: bash setup_scheduler_identity_gap.sh

echo "=========================================="
echo "Configuración de Scheduler: Identity Gap Recovery"
echo "=========================================="

# Detectar sistema operativo
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Sistema: Linux"
    echo ""
    echo "Para configurar cron en Linux:"
    echo ""
    echo "1. Editar crontab:"
    echo "   crontab -e"
    echo ""
    echo "2. Agregar la siguiente línea (ejecuta diariamente a las 2 AM):"
    echo "   0 2 * * * cd /path/to/ct4/backend && /path/to/venv/bin/python -m jobs.retry_identity_matching 500 >> /var/log/identity_gap_recovery.log 2>&1"
    echo ""
    echo "3. Para ejecutar cada 6 horas:"
    echo "   0 */6 * * * cd /path/to/ct4/backend && /path/to/venv/bin/python -m jobs.retry_identity_matching 500 >> /var/log/identity_gap_recovery.log 2>&1"
    echo ""
    echo "4. Verificar que cron está corriendo:"
    echo "   systemctl status cron"
    echo ""
    echo "5. Ver logs:"
    echo "   tail -f /var/log/identity_gap_recovery.log"
    
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Sistema: Windows"
    echo ""
    echo "Para configurar Task Scheduler en Windows:"
    echo ""
    echo "1. Abrir Task Scheduler (taskschd.msc)"
    echo ""
    echo "2. Crear nueva tarea básica:"
    echo "   - Nombre: Identity Gap Recovery"
    echo "   - Descripción: Ejecuta job de recovery de identity gap diariamente"
    echo ""
    echo "3. Trigger:"
    echo "   - Diariamente a las 2:00 AM"
    echo ""
    echo "4. Acción:"
    echo "   - Programa: python.exe"
    echo "   - Argumentos: -m jobs.retry_identity_matching 500"
    echo "   - Directorio de inicio: C:\\path\\to\\ct4\\backend"
    echo ""
    echo "5. Condiciones:"
    echo "   - Iniciar la tarea solo si el equipo está conectado a la alimentación de CA"
    echo ""
    echo "6. Configuración:"
    echo "   - Permitir ejecutar la tarea a petición"
    echo "   - Si la tarea falla, reiniciar cada: 1 hora"
    echo ""
    echo "7. Alternativa con PowerShell (ejecutar como administrador):"
    echo "   \$action = New-ScheduledTaskAction -Execute 'python.exe' -Argument '-m jobs.retry_identity_matching 500' -WorkingDirectory 'C:\\path\\to\\ct4\\backend'"
    echo "   \$trigger = New-ScheduledTaskTrigger -Daily -At 2am"
    echo "   Register-ScheduledTask -TaskName 'Identity Gap Recovery' -Action \$action -Trigger \$trigger"
    
else
    echo "Sistema no reconocido: $OSTYPE"
    echo "Ver documentación en docs/runbooks/identity_gap_recovery.md"
fi

echo ""
echo "=========================================="
echo "Configuración completada"
echo "=========================================="
