#!/bin/bash
# Script de configuración para Job Recurrente de Scout Attribution
# Linux Cron

echo "========================================"
echo "Configuración Job Recurrente Scout Attribution"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/ops_refresh_scout_attribution.py"

echo "Script: $SCRIPT_PATH"
echo "Proyecto: $PROJECT_ROOT"
echo ""

# Verificar que el script existe
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "[ERROR] Script no encontrado: $SCRIPT_PATH"
    exit 1
fi

# Hacer ejecutable
chmod +x "$SCRIPT_PATH"

echo "Para configurar el job recurrente en cron:"
echo ""
echo "1. Edita crontab:"
echo "   crontab -e"
echo ""
echo "2. Agrega esta línea (ejecutar cada 4 horas):"
echo "   0 */4 * * * cd $PROJECT_ROOT && python $SCRIPT_PATH >> /var/log/scout_refresh.log 2>&1"
echo ""
echo "3. Verificar logs:"
echo "   tail -f /var/log/scout_refresh.log"
echo ""
echo "O ejecuta manualmente:"
echo "   cd $PROJECT_ROOT"
echo "   python $SCRIPT_PATH"
echo ""

# Probar ejecución manual
read -p "¿Deseas probar la ejecución ahora? (S/N): " response
if [ "$response" = "S" ] || [ "$response" = "s" ]; then
    echo ""
    echo "Ejecutando script..."
    cd "$PROJECT_ROOT"
    python "$SCRIPT_PATH"
fi

